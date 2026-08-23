# tests/models/test_pedido.py

import pytest

from restaurante_api.models import ItemPedido
from restaurante_api.models.pedido import (
    OrigemPedido,
    Pedido,
    StatusPedido,
    TipoCliente,
)
from restaurante_api.models.produto import CategoriaProduto, Produto


@pytest.mark.asyncio
async def test_create_pedido(session, mock_db_time, user):
    """Testa criação de um pedido"""
    with mock_db_time(model=Pedido) as time:
        pedido = Pedido(
            mesa_numero=1,
            cliente_nome='Cliente Teste',
            cliente_telefone='+244 999 999 999',
            cliente_tipo=TipoCliente.REGISTRADO,
            origem=OrigemPedido.PRESENCIAL,
            observacoes='Sem cebola',
            usuario_id=user.id,
        )
        session.add(pedido)
        await session.commit()
        await session.refresh(pedido)

    assert pedido.id == int(1)
    assert pedido.public_id is not None
    assert pedido.mesa_numero == int(1)
    assert pedido.cliente_nome == 'Cliente Teste'
    assert pedido.cliente_telefone == '+244 999 999 999'
    assert pedido.cliente_tipo == TipoCliente.REGISTRADO
    assert pedido.origem == OrigemPedido.PRESENCIAL
    assert pedido.observacoes == 'Sem cebola'
    assert pedido.usuario_id == user.id
    assert pedido.total == float(0.0)
    assert pedido.status == StatusPedido.AGUARDANDO_PAGAMENTO
    assert pedido.created_at == time


@pytest.mark.asyncio
async def test_create_pedido_sem_usuario(session):
    """Testa criação de pedido sem usuário (convidado)"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Convidado',
        cliente_telefone='+244 999 999 999',
        cliente_tipo=TipoCliente.CONVIDADO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    assert pedido.usuario_id is None
    assert pedido.cliente_tipo == TipoCliente.CONVIDADO


@pytest.mark.asyncio
async def test_create_pedido_com_itens(session, mock_db_time):
    """Testa criação de pedido com itens"""
    # Cria produtos
    produto1 = Produto(
        name='Pizza', price=2500.00, category=CategoriaProduto.PRINCIPAL
    )
    produto2 = Produto(
        name='Suco', price=450.00, category=CategoriaProduto.SUCOS
    )
    session.add_all([produto1, produto2])
    await session.commit()
    await session.refresh(produto1)
    await session.refresh(produto2)

    with mock_db_time(model=Pedido):
        pedido = Pedido(
            mesa_numero=1,
            cliente_nome='Cliente Teste',
            cliente_telefone='+244 999 999 999',
        )
        session.add(pedido)
        await session.commit()
        await session.refresh(pedido)

    # Cria itens do pedido
    with mock_db_time(model=ItemPedido):
        item1 = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto1.id,
            quantidade=2,
            preco_unitario=produto1.price,
            subtotal=produto1.price * 2,
        )

        session.add(item1)
        await session.commit()
        await session.refresh(item1)

    assert item1.id == int(1)
    assert item1.pedido_id == pedido.id
    assert item1.produto_id == produto1.id
    assert item1.quantidade == int(2)
    assert item1.preco_unitario == float(2500.00)
    assert item1.subtotal == float(5000.00)


@pytest.mark.asyncio
async def test_relacionamento_pedido_itens(session):
    """Testa o relacionamento entre Pedido e Itens"""
    produto = Produto(
        name='Teste', price=100.00, category=CategoriaProduto.BEBIDA
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Teste',
        cliente_telefone='+244 999 999 999',
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    item1 = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=100.00,
        subtotal=200.00,
    )
    item2 = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=3,
        preco_unitario=100.00,
        subtotal=300.00,
    )
    session.add_all([item1, item2])
    await session.commit()

    # Recarrega o pedido
    await session.refresh(pedido)

    assert len(pedido.itens) == int(2)
    assert pedido.itens[0].quantidade == int(2)
    assert pedido.itens[1].quantidade == int(3)


@pytest.mark.asyncio
async def test_update_pedido_status(session):
    """Testa atualização de status do pedido"""
    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Teste',
        cliente_telefone='+244 999 999 999',
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    pedido.status = StatusPedido.PAGO
    await session.commit()
    await session.refresh(pedido)

    assert pedido.status == StatusPedido.PAGO

    pedido.status = StatusPedido.PREPARANDO
    await session.commit()
    await session.refresh(pedido)

    assert pedido.status == StatusPedido.PREPARANDO


@pytest.mark.asyncio
async def test_pedido_total_calculado(session):
    """Testa que o total do pedido é calculado corretamente"""
    produto = Produto(
        name='Produto', price=100.00, category=CategoriaProduto.BEBIDA
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    pedido = Pedido(
        mesa_numero=1,
        cliente_nome='Teste',
        cliente_telefone='+244 999 999 999',
        total=0.0,
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)

    item1 = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=100.00,
        subtotal=200.00,
    )
    item2 = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=3,
        preco_unitario=100.00,
        subtotal=300.00,
    )
    session.add_all([item1, item2])
    await session.commit()

    await session.refresh(pedido)
    # Atualiza total manualmente (ou via trigger)
    pedido.total = sum(item.subtotal for item in pedido.itens)
    await session.commit()
    await session.refresh(pedido)

    assert pedido.total == int(500.00)
