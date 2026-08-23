# tests/routes/test_pedidos.py

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
import pytest_asyncio

from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.pedido import Pedido, StatusPedido
from restaurante_api.models.produto import CategoriaProduto, Produto
from restaurante_api.models.reserva_mesa import ReservaMesa

# ============================================================
# FIXTURES AUXILIARES
# ============================================================


@pytest_asyncio.fixture
async def produtos_base(session):
    """Cria produtos base para testes"""
    produtos = [
        Produto(
            name='Pizza',
            price=2500.00,
            category=CategoriaProduto.PRINCIPAL,
            is_available=True,
        ),
        Produto(
            name='Suco',
            price=450.00,
            category=CategoriaProduto.SUCOS,
            is_available=True,
        ),
        Produto(
            name='Cerveja',
            price=380.00,
            category=CategoriaProduto.CERVEJA,
            is_available=True,
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()
    for p in produtos:
        await session.refresh(p)
    return produtos


# ============================================================
# TESTES DE LISTAGEM
# ============================================================


@pytest.mark.asyncio
async def test_listar_pedidos_admin(client, session, admin_token, admin_user):
    """Testa listagem de pedidos como admin (vê todos)"""
    # Cria pedidos
    pedido1 = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Admin',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    pedido2 = Pedido(
        mesa_numero=2,
        cliente_nome='Cliente Convidado',
        cliente_telefone='+244 999 999 998',
        usuario_id=None,
        total=450.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add_all([pedido1, pedido2])
    await session.commit()

    response = client.get(
        '/pedidos/', headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)


@pytest.mark.asyncio
async def test_listar_pedidos_usuario_comum(client, session, token, user):
    """Testa listagem de pedidos como usuário comum (vê apenas os próprios)"""
    pedido1 = Pedido(
        mesa_numero=1,
        cliente_nome='Meu Pedido',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    pedido2 = Pedido(
        mesa_numero=2,
        cliente_nome='Outro Pedido',
        cliente_telefone='+244 999 999 998',
        usuario_id=None,
        total=450.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add_all([pedido1, pedido2])
    await session.commit()

    response = client.get(
        '/pedidos/', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['cliente_nome'] == 'Meu Pedido'


@pytest.mark.asyncio
async def test_listar_pedidos_sem_autenticacao(client):
    """Testa listagem de pedidos sem token (deve falhar)"""
    response = client.get('/pedidos/')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_listar_pedidos_com_filtro_status(
    client, session, admin_token, admin_user
):
    """Testa listagem com filtro por status"""
    pedido1 = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente 1',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=100.00,
        status=StatusPedido.PAGO,
    )
    pedido2 = Pedido(
        mesa_numero=2,
        cliente_nome='Cliente 2',
        cliente_telefone='+244 999 999 998',
        usuario_id=admin_user.id,
        total=200.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add_all([pedido1, pedido2])
    await session.commit()

    response = client.get(
        '/pedidos/?status=pago',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['status'] == 'pago'


# ============================================================
# TESTES DE BUSCA
# ============================================================


@pytest.mark.asyncio
async def test_buscar_pedido_por_public_id(
    client, session, admin_token, admin_user
):
    """Testa busca de pedido por public_id"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pedidos/{pedido.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == pedido.public_id
    assert data['cliente_nome'] == 'Cliente Teste'
    assert data['total'] == int(2500.00)


@pytest.mark.asyncio
async def test_buscar_pedido_public_id_nao_encontrado(client, admin_token):
    """Testa busca de pedido com public_id inexistente"""
    response = client.get(
        '/pedidos/00000000-0000-0000-0000-000000000000',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_buscar_pedido_sem_permissao(client, session, token, admin_user):
    """Testa busca de pedido de outro usuário (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Pedido Admin',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.get(
        f'/pedidos/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE CRIAÇÃO
# ============================================================


@pytest.mark.asyncio
async def test_criar_pedido(client, token, user, produtos_base):
    """Testa criação de pedido com itens"""
    produto = produtos_base[0]
    pedido_data = {
        'mesa_numero': int(1),
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'observacoes': 'Sem cebola',
        'origem': 'presencial',
        'usuario_id': user.id,
        'itens': [
            {
                'produto_id': produto.id,
                'quantidade': int(2),
            }
        ],
    }
    print('produto_base: ', produtos_base)
    print('prduto.id: ', produto.id)
    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['mesa_numero'] == int(1)
    assert data['cliente_nome'] == 'Cliente Teste'
    assert data['total'] == int(5000.00)  # 2 * 2500
    assert data['status'] == 'aguardando_pagamento'
    assert len(data['itens']) == int(1)


@pytest.mark.asyncio
async def test_criar_pedido_com_reserva(
    client, session, token, user, produtos_base
):
    """Testa criação de pedido associado a uma reserva"""
    # Cria mesa e reserva
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.RESERVADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
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

    pedido_data = {
        'mesa_numero': 1,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'origem': 'reserva',
        'usuario_id': user.id,
        'reserva_mesa_id': reserva.id,
        'itens': [
            {
                'produto_id': produto.id,
                'quantidade': 1,
            }
        ],
    }

    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['reserva_mesa_id'] == reserva.id

    # Verifica que a reserva foi atualizada
    await session.refresh(reserva)
    assert reserva.status == StatusMesa.CONFIRMADA


@pytest.mark.asyncio
async def test_criar_pedido_produto_indisponivel(client, session, token, user):
    """Testa criação de pedido com produto indisponível"""
    produto = Produto(
        name='Produto Indisponível',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
        is_available=False,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    pedido_data = {
        'mesa_numero': 1,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'usuario_id': user.id,
        'itens': [
            {
                'produto_id': produto.id,
                'quantidade': 1,
            }
        ],
    }

    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'não está disponível' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_pedido_produto_inexistente(client, token, user):
    """Testa criação de pedido com produto inexistente"""
    pedido_data = {
        'mesa_numero': 1,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'usuario_id': user.id,
        'itens': [
            {
                'produto_id': 999,
                'quantidade': 1,
            }
        ],
    }

    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_pedido_sem_itens(client, token, user):
    """Testa criação de pedido sem itens (deve falhar)"""
    pedido_data = {
        'mesa_numero': 1,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'usuario_id': user.id,
        'itens': [],
    }

    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_criar_pedido_reserva_inexistente(
    client, token, user, produtos_base
):
    """Testa criação de pedido com reserva inexistente"""
    produto = produtos_base[0]

    pedido_data = {
        'mesa_numero': 1,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'cliente_tipo': 'registrado',
        'usuario_id': user.id,
        'reserva_mesa_id': 999,
        'itens': [
            {
                'produto_id': produto.id,
                'quantidade': 1,
            }
        ],
    }

    response = client.post(
        '/pedidos/',
        headers={'Authorization': f'Bearer {token}'},
        json=pedido_data,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


# ============================================================
# TESTES DE ATUALIZAÇÃO
# ============================================================


@pytest.mark.asyncio
async def test_atualizar_pedido(client, session, admin_token, admin_user):
    """Testa atualização de pedido"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Original',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    update_data = {
        'cliente_nome': 'Cliente Atualizado',
        'observacoes': 'Observação atualizada',
    }

    response = client.put(
        f'/pedidos/{pedido.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=update_data,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['cliente_nome'] == 'Cliente Atualizado'
    assert data['observacoes'] == 'Observação atualizada'


@pytest.mark.asyncio
async def test_atualizar_pedido_sem_permissao(
    client, session, token, admin_user
):
    """Testa atualização de pedido de outro usuário (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Pedido Admin',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.put(
        f'/pedidos/{pedido.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'cliente_nome': 'Hackeado'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE STATUS
# ============================================================


@pytest.mark.asyncio
async def test_atualizar_status_pedido(
    client, session, admin_token, admin_user
):
    """Testa atualização de status do pedido (admin)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/status',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'status': 'pago'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == 'pago'


@pytest.mark.asyncio
async def test_atualizar_status_pedido_usuario_comum(
    client, session, token, user
):
    """Testa atualização de status por usuário comum (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/status',
        headers={'Authorization': f'Bearer {token}'},
        json={'status': 'pago'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


# ============================================================
# TESTES DE CANCELAMENTO
# ============================================================


@pytest.mark.asyncio
async def test_cancelar_pedido(client, session, admin_token, admin_user):
    """Testa cancelamento de pedido (admin)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/cancelar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == 'cancelado'


@pytest.mark.asyncio
async def test_cancelar_pedido_usuario_comum(client, session, token, user):
    """Testa cancelamento de pedido pelo próprio usuário"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Meu Pedido',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/cancelar',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == 'cancelado'


@pytest.mark.asyncio
async def test_cancelar_pedido_ja_entregue(
    client, session, admin_token, admin_user
):
    """Testa cancelamento de pedido já entregue (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.ENTREGUE,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/cancelar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'não é possível cancelar' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_cancelar_pedido_sem_permissao(
    client, session, token, admin_user
):
    """Testa cancelamento de pedido de outro usuário (deve falhar)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Pedido Admin',
        cliente_telefone='+244 999 999 999',
        usuario_id=admin_user.id,
        total=2500.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    response = client.patch(
        f'/pedidos/{pedido.public_id}/cancelar',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE MEUS PEDIDOS
# ============================================================


@pytest.mark.asyncio
async def test_meus_pedidos(client, session, token, user):
    """Testa listagem de meus pedidos"""
    pedido1 = Pedido(
        mesa_numero=1,
        cliente_nome='Meu Pedido 1',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    pedido2 = Pedido(
        mesa_numero=2,
        cliente_nome='Meu Pedido 2',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=450.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    pedido3 = Pedido(
        mesa_numero=3,
        cliente_nome='Outro Pedido',
        cliente_telefone='+244 999 999 997',
        usuario_id=None,
        total=380.00,
        status=StatusPedido.PAGO,
    )
    session.add_all([pedido1, pedido2, pedido3])
    await session.commit()

    response = client.get(
        '/pedidos/listar/meus', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)
    assert all(p['cliente_nome'].startswith('Meu Pedido') for p in data)


@pytest.mark.asyncio
async def test_meus_pedidos_com_filtro_status(client, session, token, user):
    """Testa meus pedidos com filtro por status"""
    pedido1 = Pedido(
        mesa_numero=1,
        cliente_nome='Meu Pedido Pago',
        cliente_telefone='+244 999 999 999',
        usuario_id=user.id,
        total=2500.00,
        status=StatusPedido.PAGO,
    )
    pedido2 = Pedido(
        mesa_numero=2,
        cliente_nome='Meu Pedido Pendente',
        cliente_telefone='+244 999 999 998',
        usuario_id=user.id,
        total=450.00,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add_all([pedido1, pedido2])
    await session.commit()

    response = client.get(
        '/pedidos/listar/meus?status_pedido=pago',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['cliente_nome'] == 'Meu Pedido Pago'
    assert data[0]['status'] == 'pago'
