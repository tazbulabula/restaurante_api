# tests/routes/test_pagamento_manual.py

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest

from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.pedido import MetodoPagamento, Pedido, StatusPedido
from restaurante_api.models.reserva_mesa import ReservaMesa


@pytest.mark.asyncio
async def test_pagamento_manual_dinheiro(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual em dinheiro"""
    # Cria um pedido aguardando pagamento
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price * 2,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=admin_user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    # Dados do pagamento manual
    dados = {
        'metodo': 'dinheiro',
        'observacao': 'Pagamento em dinheiro recebido no balcão',
    }

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Pagamento via dinheiro registrado com sucesso'
    assert data['pedido_id'] == pedido.id
    assert data['metodo'] == 'dinheiro'

    # Verifica no banco
    await session.refresh(pedido)
    assert pedido.status == StatusPedido.PAGO
    assert pedido.metodo_pagamento == MetodoPagamento.DINHEIRO
    assert pedido.pagamento_manual is True
    assert pedido.pagamento_autorizado_por == admin_user.username
    assert pedido.codigo_autorizacao.startswith('MANUAL-DINHEIRO-')


@pytest.mark.asyncio
async def test_pagamento_manual_transferencia(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual por transferência bancária"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=admin_user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {
        'metodo': 'transferencia',
        'observacao': 'Transferência confirmada via comprovante',
    }

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['metodo'] == 'transferencia'

    await session.refresh(pedido)
    assert pedido.status == StatusPedido.PAGO
    assert pedido.metodo_pagamento == MetodoPagamento.TRANSFERENCIA
    assert pedido.pagamento_manual is True


@pytest.mark.asyncio
async def test_pagamento_manual_pos(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual via POS (cartão)"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=admin_user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {'metodo': 'pos', 'observacao': 'Pagamento com cartão de débito'}

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['metodo'] == 'pos'

    await session.refresh(pedido)
    assert pedido.status == StatusPedido.PAGO
    assert pedido.metodo_pagamento == MetodoPagamento.POS
    assert pedido.pagamento_manual is True


@pytest.mark.asyncio
async def test_pagamento_manual_pedido_nao_encontrado(client, admin_token):
    """Testa pagamento manual para pedido inexistente"""
    dados = {'metodo': 'dinheiro', 'observacao': 'Pagamento em dinheiro'}

    response = client.patch(
        '/pedidos/00000000-0000-0000-0000-000000000000/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'Pedido não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_pagamento_manual_pedido_ja_pago(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual para pedido já pago (deve falhar)"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.PAGO,  # Já pago
        usuario_id=admin_user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {'metodo': 'dinheiro', 'observacao': 'Tentando pagar novamente'}

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'Pedido não está aguardando pagamento' in response.json()['detail']


@pytest.mark.asyncio
async def test_pagamento_manual_sem_autenticacao(
    client, session, produtos_base
):
    """Testa pagamento manual sem token (deve falhar)"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {'metodo': 'dinheiro', 'observacao': 'Pagamento em dinheiro'}

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual', json=dados
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_pagamento_manual_usuario_comum(
    client, session, token, user, produtos_base
):
    """Testa pagamento manual com usuário comum (deve falhar - apenas admin)"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {
        'metodo': 'dinheiro',
        'observacao': 'Tentativa de pagamento manual',
    }

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_pagamento_manual_metodo_invalido(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual com método inválido"""
    produto = produtos_base[0]
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=admin_user.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {'metodo': 'metodo_invalido', 'observacao': 'Método inválido'}

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_pagamento_manual_com_reserva_associada(
    client, session, admin_token, admin_user, produtos_base
):
    """Testa pagamento manual com reserva associada"""
    # Cria mesa e reserva
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.RESERVADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Cliente Reserva',
        cliente_telefone='+244 999 999 999',
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
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        total=produto.price,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        usuario_id=admin_user.id,
        reserva_mesa_id=reserva.id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    dados = {
        'metodo': 'dinheiro',
        'observacao': 'Pagamento em dinheiro com reserva',
    }

    response = client.patch(
        f'/pedidos/{pedido.public_id}/pagamento-manual',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=dados,
    )

    assert response.status_code == HTTPStatus.OK

    # Verifica que a reserva foi confirmada
    await session.refresh(reserva)
    assert reserva.status == StatusMesa.CONFIRMADA
