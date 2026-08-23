# tests/routes/test_pagamento.py
import asyncio
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch

import pytest
import pytest_asyncio

from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.pedido import Pedido, StatusPedido
from restaurante_api.models.reserva_mesa import ReservaMesa

# ============================================================
# FIXTURE AUXILIAR
# ============================================================


@pytest_asyncio.fixture
async def pedido_pendente(session, user, produtos_base):
    """Cria um pedido pendente para testes de pagamento"""
    produto = produtos_base[0]

    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=produto.price * 2,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)
    return pedido


@pytest_asyncio.fixture
async def pedido_pendente_com_reserva(session, user, produtos_base):
    """Cria um pedido pendente com reserva associada"""
    # Cria mesa e reserva
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.RESERVADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome="Cliente Reserva",
        cliente_telefone="+244 999 999 999",
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    produto = produtos_base[0]

    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        reserva_mesa_id=reserva.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)
    return pedido, reserva


# ============================================================
# TESTES DE INICIAR PAGAMENTO
# ============================================================

@pytest.mark.asyncio
async def test_iniciar_pagamento_sucesso(
        client, session, token, pedido_pendente
):
    """Testa início de pagamento com sucesso"""
    request_data = {
        "pedido_public_id": pedido_pendente.public_id,
        "telefone": "+244 999 999 999",
    }

    # Mock do serviço EMIS
    with patch(
            "restaurante_api.services.pagamento.EMISService.iniciar_pagamento"
    ) as mock_iniciar:
        mock_iniciar.return_value = {
            "transacao_id": "TRX123456",
            "status": "PENDENTE",
            "mensagem": "Pagamento iniciado com sucesso",
        }

        response = client.post(
            '/pagamento/iniciar',
            headers={'Authorization': f'Bearer {token}'},
            json=request_data,
        )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['transacao_id'] == "TRX123456"
    assert data['pedido_public_id'] == pedido_pendente.public_id
    assert data['valor'] == pedido_pendente.total
    assert data['status'] == "PENDENTE"

    # Verifica que o pedido foi atualizado
    await session.refresh(pedido_pendente)
    assert pedido_pendente.transacao_id == "TRX123456"
    assert pedido_pendente.cliente_telefone == "+244 999 999 999"


@pytest.mark.asyncio
async def test_iniciar_pagamento_sem_autenticacao(client):
    """Testa início de pagamento sem token (deve falhar)"""
    request_data = {
        "pedido_public_id": "fake-id",
        "telefone": "+244 999 999 999",
    }

    response = client.post('/pagamento/iniciar', json=request_data)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_iniciar_pagamento_pedido_inexistente(client, token):
    """Testa início de pagamento com pedido inexistente"""
    request_data = {
        "pedido_public_id": "00000000-0000-0000-0000-000000000000",
        "telefone": "+244 999 999 999",
    }

    response = client.post(
        '/pagamento/iniciar',
        headers={'Authorization': f'Bearer {token}'},
        json=request_data,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_iniciar_pagamento_pedido_outro_usuario(
        client, session, token, admin_user,
):
    """Testa início de pagamento de pedido de outro usuário (deve falhar)"""
    # Cria pedido de outro usuário
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Pedido Admin",
        cliente_telefone="+244 999 999 999",
        usuario_id=admin_user.id,
        total=100.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    request_data = {
        "pedido_public_id": pedido.public_id,
        "telefone": "+244 999 999 999",
    }

    response = client.post(
        '/pagamento/iniciar',
        headers={'Authorization': f'Bearer {token}'},
        json=request_data,
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_iniciar_pagamento_pedido_ja_pago(client, session, token, user):
    """Testa início de pagamento de pedido já pago (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=100.00,
        status=StatusPedido.PAGO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    request_data = {
        "pedido_public_id": pedido.public_id,
        "telefone": "+244 999 999 999",
    }

    response = client.post(
        '/pagamento/iniciar',
        headers={'Authorization': f'Bearer {token}'},
        json=request_data,
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'já está com status' in response.json()['detail']


@pytest.mark.asyncio
async def test_iniciar_pagamento_valor_invalido(client, session, token, user):
    """Testa início de pagamento com valor inválido (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=0.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    request_data = {
        "pedido_public_id": pedido.public_id,
        "telefone": "+244 999 999 999",
    }

    response = client.post(
        '/pagamento/iniciar',
        headers={'Authorization': f'Bearer {token}'},
        json=request_data,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'valor inválido' in response.json()['detail'].lower()


# ============================================================
# TESTES DE CALLBACK
# ============================================================

@pytest.mark.asyncio
async def test_callback_pagamento_aprovado(client, session, pedido_pendente):
    """Testa callback de pagamento aprovado"""
    callback_data = {
        "transacao_id": "TRX123456",
        "status": "APROVADO",
        "valor": pedido_pendente.total,
        "codigo_autorizacao": "AUTH123",
        "mensagem": "Pagamento aprovado",
        "data_hora": datetime.now().isoformat(),
    }

    # Salva o transacao_id no pedido
    pedido_pendente.transacao_id = "TRX123456"
    await session.commit()

    response = client.post(
        '/pagamento/callback',
        json=callback_data,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == "OK"
    assert data['transacao_id'] == "TRX123456"

    # Aguarda processamento em background
    await asyncio.sleep(0.5)

    # Verifica que o pedido foi atualizado
    await session.refresh(pedido_pendente)
    assert pedido_pendente.status == StatusPedido.PAGO
    assert pedido_pendente.codigo_autorizacao == "AUTH123"


@pytest.mark.asyncio
async def test_callback_pagamento_aprovado_com_reserva(
        client, session, pedido_pendente_com_reserva
):
    """Testa callback de pagamento aprovado com reserva associada"""
    pedido, reserva = pedido_pendente_com_reserva

    callback_data = {
        "transacao_id": "TRX123456",
        "status": "APROVADO",
        "valor": pedido.total,
        "codigo_autorizacao": "AUTH123",
        "mensagem": "Pagamento aprovado",
        "data_hora": datetime.now().isoformat(),
    }

    # Salva o transacao_id no pedido
    pedido.transacao_id = "TRX123456"
    await session.commit()

    response = client.post(
        '/pagamento/callback',
        json=callback_data,
    )

    assert response.status_code == HTTPStatus.OK

    # Aguarda processamento em background
    await asyncio.sleep(0.5)

    # Verifica que o pedido foi atualizado
    await session.refresh(pedido)
    assert pedido.status == StatusPedido.PAGO

    # Verifica que a reserva foi confirmada
    await session.refresh(reserva)
    assert reserva.status == StatusMesa.CONFIRMADA


@pytest.mark.asyncio
async def test_callback_pagamento_rejeitado(client, session, pedido_pendente):
    """Testa callback de pagamento rejeitado"""
    callback_data = {
        "transacao_id": "TRX123456",
        "status": "REJEITADO",
        "valor": pedido_pendente.total,
        "mensagem": "Saldo insuficiente",
        "data_hora": datetime.now().isoformat(),
    }

    # Salva o transacao_id no pedido
    pedido_pendente.transacao_id = "TRX123456"
    await session.commit()

    response = client.post(
        '/pagamento/callback',
        json=callback_data,
    )

    assert response.status_code == HTTPStatus.OK

    # Aguarda processamento em background
    await asyncio.sleep(0.5)

    # Verifica que o pedido continua aguardando pagamento
    await session.refresh(pedido_pendente)
    assert pedido_pendente.status == StatusPedido.AGUARDANDO_PAGAMENTO


@pytest.mark.asyncio
async def test_callback_pagamento_cancelado(client, session, pedido_pendente):
    """Testa callback de pagamento cancelado"""
    callback_data = {
        "transacao_id": "TRX123456",
        "status": "CANCELADO",
        "valor": pedido_pendente.total,
        "mensagem": "Pagamento cancelado pelo usuário",
        "data_hora": datetime.now().isoformat(),
    }

    # Salva o transacao_id no pedido
    pedido_pendente.transacao_id = "TRX123456"
    await session.commit()

    response = client.post(
        '/pagamento/callback',
        json=callback_data,
    )

    assert response.status_code == HTTPStatus.OK

    # Aguarda processamento em background
    await asyncio.sleep(0.5)

    # Verifica que o pedido continua aguardando pagamento
    await session.refresh(pedido_pendente)
    assert pedido_pendente.status == StatusPedido.AGUARDANDO_PAGAMENTO


@pytest.mark.asyncio
async def test_callback_pedido_nao_encontrado(client):
    """Testa callback com transacao_id não encontrado"""
    callback_data = {
        "transacao_id": "TRX_INEXISTENTE",
        "status": "APROVADO",
        "valor": 100.00,
        "data_hora": datetime.now().isoformat(),
    }

    response = client.post('/pagamento/callback', json=callback_data)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


# ============================================================
# TESTES DE CONSULTAR STATUS
# ============================================================

@pytest.mark.asyncio
async def test_consultar_status_pagamento(
        client, token, pedido_pendente
):
    """Testa consulta de status do pagamento"""
    response = client.get(
        f'/pagamento/status/{pedido_pendente.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['pedido_public_id'] == pedido_pendente.public_id
    assert data['status_pedido'] == 'aguardando_pagamento'
    assert data['valor'] == pedido_pendente.total
    assert 'Aguardando confirmação' in data['mensagem']


@pytest.mark.asyncio
async def test_consultar_status_pagamento_pago(client, session, token, user):
    """Testa consulta de status de pedido pago"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=100.00,
        status=StatusPedido.PAGO,
        transacao_id="TRX123456",
        pagamento_confirmado_em=datetime.now(),
        codigo_autorizacao="AUTH123",
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pagamento/status/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status_pedido'] == 'pago'
    assert data['transacao_id'] == "TRX123456"
    assert data['codigo_autorizacao'] == "AUTH123"
    assert 'Pagamento confirmado' in data['mensagem']


@pytest.mark.asyncio
async def test_consultar_status_pagamento_entregue(
        client, session, token, user
):
    """Testa consulta de status de pedido entregue"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=100.00,
        status=StatusPedido.ENTREGUE,
        transacao_id="TRX123456",
        pagamento_confirmado_em=datetime.now(),
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pagamento/status/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status_pedido'] == 'entregue'
    assert 'Obrigado' in data['mensagem']


@pytest.mark.asyncio
async def test_consultar_status_pagamento_cancelado(
        client, session, token, user
):
    """Testa consulta de status de pedido cancelado"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Cliente Teste",
        cliente_telefone="+244 999 999 999",
        usuario_id=user.id,
        total=100.00,
        status=StatusPedido.CANCELADO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pagamento/status/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status_pedido'] == 'cancelado'
    assert 'cancelado' in data['mensagem'].lower()


@pytest.mark.asyncio
async def test_consultar_status_pagamento_nao_encontrado(client, token):
    """Testa consulta de status com pedido inexistente"""
    response = client.get(
        '/pagamento/status/00000000-0000-0000-0000-000000000000',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_consultar_status_pagamento_sem_permissao(
        client, session, token, admin_user
):
    """Testa consulta de status de pedido de outro usuário (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome="Pedido Admin",
        cliente_telefone="+244 999 999 999",
        usuario_id=admin_user.id,
        total=100.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pagamento/status/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE ADMIN PODE VER TODOS
# ============================================================

@pytest.mark.asyncio
async def test_iniciar_pagamento_admin_por_outro_usuario(
        client, token, pedido_pendente
):
    """Testa que admin pode iniciar pagamento de pedido de outro usuário"""
    request_data = {
        "pedido_public_id": pedido_pendente.public_id,
        "telefone": "+244 999 999 999",
    }

    with patch(
            "restaurante_api.services.pagamento.EMISService.iniciar_pagamento"
    ) as mock_iniciar:
        mock_iniciar.return_value = {
            "transacao_id": "TRX123456",
            "status": "PENDENTE",
            "mensagem": "Pagamento iniciado com sucesso",
        }

        response = client.post(
            '/pagamento/iniciar',
            headers={'Authorization': f'Bearer {token}'},
            json=request_data,
        )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['transacao_id'] == "TRX123456"


@pytest.mark.asyncio
async def test_consultar_status_admin_por_outro_usuario(
        client, admin_token, pedido_pendente
):
    """Testa que admin pode consultar status de pedido de outro usuário"""
    response = client.get(
        f'/pagamento/status/{pedido_pendente.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['pedido_public_id'] == pedido_pendente.public_id
