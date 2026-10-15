# tests/routes/test_dashboard.py

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from sqlalchemy import select

from restaurante_api.core.security import hash_password as get_password_hash
from restaurante_api.models import (
    ItemPedido,
    Mesa,
    Pedido,
    Produto,
    ReservaMesa,
    StatusMesa,
    StatusPedido,
    User,
)
from restaurante_api.models.produto import CategoriaProduto
from restaurante_api.schemas.user import UserType


# ============================================================
# HELPERS
# ============================================================
async def _criar_produto(  # noqa: PLR0913, PLR0917
    session,
    nome: str = 'Produto',
    categoria: CategoriaProduto = CategoriaProduto.PRINCIPAL,
    disponivel: bool = True,
    preco: float = 100.0,
):
    produto = Produto(
        name=nome,
        price=preco,
        category=categoria,
        is_available=disponivel,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_pedido(  # noqa: PLR0913, PLR0917
    session,
    mesa_numero: int = 1,
    cliente_nome: str = 'Cliente',
    status: StatusPedido = StatusPedido.PAGO,
    total: float = 100.0,
    created_at: datetime | None = None,
    usuario_id: int | None = None,
):
    pedido = Pedido(
        mesa_numero=mesa_numero,
        cliente_nome=cliente_nome,
        cliente_telefone='900000000',
        status=status,
        total=total,
        usuario_id=usuario_id,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    # ⚠️ created_at é server_default — se quisermos forçar, atualizamos
    if created_at is not None:
        await session.execute(
            Pedido.__table__
            .update()
            .where(Pedido.id == pedido.id)
            .values(created_at=created_at)
        )
        await session.commit()
        await session.refresh(pedido)

    return pedido


async def _criar_item(  # noqa: PLR0913, PLR0917
    session,
    pedido_id: int,
    produto_id: int,
    quantidade: int = 1,
    preco_unitario: float = 100.0,
):
    item = ItemPedido(
        pedido_id=pedido_id,
        produto_id=produto_id,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        subtotal=preco_unitario * quantidade,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def _criar_mesa(  # noqa: PLR0913, PLR0917
    session, numero: int, status: StatusMesa = StatusMesa.DISPONIVEL
):
    mesa = Mesa(numero=numero, capacidade=4, status=status)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)
    return mesa


async def _criar_reserva(
    session,
    mesa_id: int,
    data_hora: datetime,
    status: StatusMesa = StatusMesa.RESERVADA,
    cliente_nome: str = 'Cliente Reserva',
):
    reserva = ReservaMesa(
        mesa_id=mesa_id,
        cliente_nome=cliente_nome,
        cliente_telefone='900000000',
        data_hora=data_hora,
        numero_pessoas=2,
        status=status,
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)
    return reserva


async def _criar_cliente(
    session, username: str = 'cli1', email: str = 'cli1@x.com'
):
    cliente = User(
        username=username,
        email=email,
        password=get_password_hash('senha123'),
        user_type=UserType.CLIENT,
        is_active=True,
    )
    session.add(cliente)
    await session.commit()
    await session.refresh(cliente)
    return cliente


# ============================================================
# AUTENTICAÇÃO / AUTORIZAÇÃO
# ============================================================
@pytest.mark.asyncio
async def test_dashboard_sem_token_retorna_401(client):
    """Qualquer endpoint sem token → 401"""
    endpoints = [
        '/dashboard/estatisticas',
        '/dashboard/produtos-por-categoria',
        '/dashboard/pedidos-por-dia',
        '/dashboard/receita-por-dia',
        '/dashboard/top-produtos',
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == HTTPStatus.UNAUTHORIZED, ep


@pytest.mark.asyncio
async def test_dashboard_cliente_comum_retorna_403(client, token):
    """Cliente comum não pode aceder ao dashboard"""
    endpoints = [
        '/dashboard/estatisticas',
        '/dashboard/produtos-por-categoria',
        '/dashboard/pedidos-por-dia',
        '/dashboard/receita-por-dia',
        '/dashboard/top-produtos',
    ]
    for ep in endpoints:
        r = client.get(ep, headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == HTTPStatus.FORBIDDEN, ep
        assert 'administradores' in r.json()['detail'].lower()


# ============================================================
# /estatisticas
# ============================================================
@pytest.mark.asyncio
async def test_estatisticas_bd_vazia(client, admin_token):
    """BD vazia → todos os valores a 0"""
    r = client.get(
        '/dashboard/estatisticas',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    assert data['total_produtos'] == int(0)
    assert data['produtos_disponiveis'] == int(0)
    assert data['total_mesas'] == int(0)
    assert data['mesas_ocupadas'] == int(0)
    assert data['total_pedidos'] == int(0)
    assert data['pedidos_hoje'] == int(0)
    assert data['receita_total'] == float(0.0)
    assert data['receita_hoje'] == float(0.0)
    assert data['total_reservas'] == int(0)
    assert data['reservas_hoje'] == int(0)
    assert data['total_clientes'] == int(0)


@pytest.mark.asyncio
async def test_estatisticas_com_dados(client, session, admin_token):
    """Popula BD e valida que os números estão corretos"""
    # ---------- Produtos ----------
    await _criar_produto(session, 'P1', disponivel=True)
    await _criar_produto(session, 'P2', disponivel=True)
    await _criar_produto(session, 'P3', disponivel=False)

    # ---------- Mesas ----------
    await _criar_mesa(session, 1, StatusMesa.DISPONIVEL)
    await _criar_mesa(session, 2, StatusMesa.OCUPADA)
    await _criar_mesa(session, 3, StatusMesa.OCUPADA)

    # ---------- Pedidos ----------
    # 2 pagos, 1 entregue, 1 cancelado (não deve contar)
    await _criar_pedido(session, total=100.0, status=StatusPedido.PAGO)
    await _criar_pedido(session, total=200.0, status=StatusPedido.PAGO)
    await _criar_pedido(session, total=300.0, status=StatusPedido.ENTREGUE)
    await _criar_pedido(session, total=999.0, status=StatusPedido.CANCELADO)

    # ---------- Reservas ----------
    mesa = (await session.execute(select(Mesa).limit(1))).scalar_one()
    hoje = datetime.now()
    await _criar_reserva(session, mesa.id, data_hora=hoje)
    await _criar_reserva(session, mesa.id, data_hora=hoje + timedelta(days=1))
    await _criar_reserva(
        session,
        mesa.id,
        data_hora=hoje + timedelta(days=2),
        status=StatusMesa.CANCELADA,
    )

    # ---------- Clientes ----------
    await _criar_cliente(session, 'cli1', 'cli1@x.com')
    await _criar_cliente(session, 'cli2', 'cli2@x.com')

    r = client.get(
        '/dashboard/estatisticas',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    assert data['total_produtos'] == int(3)
    assert data['produtos_disponiveis'] == int(2)
    assert data['total_mesas'] == int(3)
    assert data['mesas_ocupadas'] == int(2)
    # total_pedidos exclui cancelados: 3
    assert data['total_pedidos'] == int(3)
    # pedidos_hoje = 3 (todos criados agora)
    assert data['pedidos_hoje'] == int(3)
    # receita_total = 100 + 200 + 300 = 600 (cancelado fica fora)
    assert data['receita_total'] == float(600.0)
    assert data['receita_hoje'] == float(600.0)
    assert data['total_reservas'] == int(3)
    # reservas_hoje exclui futuras e canceladas → 1
    assert data['reservas_hoje'] == int(1)
    # o admin_token cria também um user admin — não conta como cliente
    assert data['total_clientes'] == int(2)


# ============================================================
# /produtos-por-categoria
# ============================================================
@pytest.mark.asyncio
async def test_produtos_por_categoria_vazio(client, admin_token):
    r = client.get(
        '/dashboard/produtos-por-categoria',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    assert r.json() == []


@pytest.mark.asyncio
async def test_produtos_por_categoria_agrupa_corretamente(
    client, session, admin_token
):
    await _criar_produto(session, 'A1', CategoriaProduto.PRINCIPAL, True)
    await _criar_produto(session, 'A2', CategoriaProduto.PRINCIPAL, True)
    await _criar_produto(session, 'A3', CategoriaProduto.PRINCIPAL, False)
    await _criar_produto(session, 'B1', CategoriaProduto.BEBIDA, True)
    await _criar_produto(session, 'B2', CategoriaProduto.BEBIDA, True)
    await _criar_produto(session, 'C1', CategoriaProduto.SOBREMESA, True)

    r = client.get(
        '/dashboard/produtos-por-categoria',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    # Deve vir ordenado por total desc
    mapa = {row['categoria']: row for row in data}

    assert mapa['principal']['total'] == int(3)
    assert mapa['principal']['disponiveis'] == int(2)
    assert mapa['bebida']['total'] == int(2)
    assert mapa['bebida']['disponiveis'] == int(2)
    assert mapa['sobremesa']['total'] == int(1)
    assert mapa['sobremesa']['disponiveis'] == int(1)

    # Ordenação: principal (3) > bebida (2) > sobremesa (1)
    assert data[0]['categoria'] == 'principal'


# ============================================================
# /pedidos-por-dia
# ============================================================
@pytest.mark.asyncio
async def test_pedidos_por_dia_vazio_preenche_zeros(client, admin_token):
    """Sem pedidos → devolve N dias com 0"""
    r = client.get(
        '/dashboard/pedidos-por-dia?dias=7',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    assert len(data) == int(7)
    assert all(row['total'] == int(0) for row in data)

    # Datas em ordem ascendente
    datas = [row['data'] for row in data]
    assert datas == sorted(datas)


@pytest.mark.asyncio
async def test_pedidos_por_dia_conta_corretamente(
    client, session, admin_token
):
    """3 pedidos hoje + 1 ontem + 1 cancelado (não conta)"""
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)

    await _criar_pedido(session, total=10.0, created_at=hoje)
    await _criar_pedido(session, total=20.0, created_at=hoje)
    await _criar_pedido(session, total=30.0, created_at=hoje)
    await _criar_pedido(session, total=40.0, created_at=ontem)
    await _criar_pedido(
        session,
        total=999.0,
        status=StatusPedido.CANCELADO,
        created_at=hoje,
    )

    r = client.get(
        '/dashboard/pedidos-por-dia?dias=7',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    assert len(data) == int(7)

    # Último = hoje
    hoje_iso = hoje.date().isoformat()
    ontem_iso = ontem.date().isoformat()

    por_data = {row['data']: row['total'] for row in data}
    assert por_data[hoje_iso] == int(3)
    assert por_data[ontem_iso] == int(1)


@pytest.mark.asyncio
async def test_pedidos_por_dia_valida_parametro(client, admin_token):
    """Query param dias fora dos limites → 422"""
    headers = {'Authorization': f'Bearer {admin_token}'}

    # dias=0 é inválido
    r = client.get('/dashboard/pedidos-por-dia?dias=0', headers=headers)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # dias=91 é inválido
    r = client.get('/dashboard/pedidos-por-dia?dias=91', headers=headers)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # dias=1 é válido
    r = client.get('/dashboard/pedidos-por-dia?dias=1', headers=headers)
    assert r.status_code == HTTPStatus.OK
    assert len(r.json()) == int(1)


# ============================================================
# /receita-por-dia
# ============================================================
@pytest.mark.asyncio
async def test_receita_por_dia_soma_corretamente(client, session, admin_token):
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)

    # Hoje: 100 + 200 = 300
    await _criar_pedido(session, total=100.0, created_at=hoje)
    await _criar_pedido(session, total=200.0, created_at=hoje)
    # Ontem: 500
    await _criar_pedido(session, total=500.0, created_at=ontem)
    # Cancelado hoje: NÃO conta
    await _criar_pedido(
        session,
        total=9999.0,
        status=StatusPedido.CANCELADO,
        created_at=hoje,
    )
    # Aguardando pagamento: NÃO conta
    await _criar_pedido(
        session,
        total=8888.0,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        created_at=hoje,
    )

    r = client.get(
        '/dashboard/receita-por-dia?dias=7',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert len(data) == int(7)

    por_data = {row['data']: row['total'] for row in data}
    assert por_data[hoje.date().isoformat()] == float(300.0)
    assert por_data[ontem.date().isoformat()] == float(500.0)


@pytest.mark.asyncio
async def test_receita_por_dia_vazio(client, admin_token):
    r = client.get(
        '/dashboard/receita-por-dia?dias=7',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert len(data) == int(7)
    assert all(row['total'] == float(0.0) for row in data)


# ============================================================
# /top-produtos
# ============================================================
@pytest.mark.asyncio
async def test_top_produtos_vazio(client, admin_token):
    r = client.get(
        '/dashboard/top-produtos?limite=5',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    assert r.json() == []


@pytest.mark.asyncio
async def test_top_produtos_ranking(client, session, admin_token):
    """Produto A: 10, Produto B: 5, Produto C: 3 → ranking A, B, C"""
    p_a = await _criar_produto(session, 'Pizza', preco=100.0)
    p_b = await _criar_produto(session, 'Hamburguer', preco=80.0)
    p_c = await _criar_produto(session, 'Suco', preco=30.0)

    pedido = await _criar_pedido(session, total=0.0)  # total não importa aqui

    await _criar_item(session, pedido.id, p_a.id, quantidade=4)
    await _criar_item(session, pedido.id, p_a.id, quantidade=6)
    await _criar_item(session, pedido.id, p_b.id, quantidade=5)
    await _criar_item(session, pedido.id, p_c.id, quantidade=3)

    r = client.get(
        '/dashboard/top-produtos?limite=5',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    nomes = [row['nome'] for row in data]
    totais = {row['nome']: row['total'] for row in data}

    assert nomes == ['Pizza', 'Hamburguer', 'Suco']
    assert totais['Pizza'] == int(10)
    assert totais['Hamburguer'] == int(5)
    assert totais['Suco'] == int(3)


@pytest.mark.asyncio
async def test_top_produtos_respeita_limite(client, session, admin_token):
    for i in range(5):
        p = await _criar_produto(session, f'P{i}', preco=10.0)
        pedido = await _criar_pedido(session, mesa_numero=i + 1, total=0.0)
        await _criar_item(session, pedido.id, p.id, quantidade=i + 1)

    r = client.get(
        '/dashboard/top-produtos?limite=2',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    assert len(r.json()) == int(2)


@pytest.mark.asyncio
async def test_top_produtos_ignora_pedidos_cancelados(
    client, session, admin_token
):
    """Itens de pedidos cancelados NÃO entram no ranking"""
    p = await _criar_produto(session, 'Pizza', preco=100.0)

    pedido_valido = await _criar_pedido(
        session, total=100.0, status=StatusPedido.PAGO
    )
    pedido_cancelado = await _criar_pedido(
        session, total=100.0, status=StatusPedido.CANCELADO
    )

    await _criar_item(session, pedido_valido.id, p.id, quantidade=3)
    await _criar_item(session, pedido_cancelado.id, p.id, quantidade=999)

    r = client.get(
        '/dashboard/top-produtos?limite=5',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    assert len(data) == int(1)
    assert data[0]['nome'] == 'Pizza'
    assert data[0]['total'] == int(3)  # só o válido
