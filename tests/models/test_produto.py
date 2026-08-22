# tests/models/test_produto.py

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from restaurante_api.models.produto import CategoriaProduto, Produto


@pytest.mark.asyncio
async def test_create_produto(session, mock_db_time):
    """Testa a criação de um produto com dados válidos"""
    with mock_db_time(model=Produto) as time:
        produto = Produto(
            name='Picanha Grelhada',
            description='Acompanha arroz, farofa e vinagrete',
            price=3500.00,
            category=CategoriaProduto.PRINCIPAL,
            subcategory='Carnes',
            is_available=True,
            image_url='https://exemplo.com/picanha.jpg',
        )
        session.add(produto)
        await session.commit()

    # Busca o produto no banco
    result = await session.scalar(
        select(Produto).where(Produto.name == 'Picanha Grelhada')
    )

    assert result is not None
    assert result.id == int(1)
    assert result.public_id == '00000000-0000-0000-0000-000000000000'
    assert result.name == 'Picanha Grelhada'
    assert result.description == 'Acompanha arroz, farofa e vinagrete'
    assert result.price == float(3500.00)
    assert result.category == CategoriaProduto.PRINCIPAL
    assert result.subcategory == 'Carnes'
    assert result.is_available is True
    assert result.image_url == 'https://exemplo.com/picanha.jpg'
    assert result.created_at == time
    assert result.updated_at == time


@pytest.mark.asyncio
async def test_create_produto_sem_descricao(session):
    """Testa criação de produto
    sem descrição (campo opcional)"""
    produto = Produto(
        name='Coca-Cola',
        price=350.00,
        category=CategoriaProduto.REFRIGERANTE,
        is_available=True,
    )
    session.add(produto)
    await session.commit()

    result = await session.scalar(
        select(Produto).where(Produto.name == 'Coca-Cola')
    )

    assert result is not None
    assert result.description is None
    assert result.subcategory is None
    assert result.image_url is None


@pytest.mark.asyncio
async def test_create_produto_sem_imagem(session):
    """Testa criação de produto
    sem imagem (campo opcional)"""
    produto = Produto(
        name='Suco de Maracujá',
        price=450.00,
        category=CategoriaProduto.SUCOS,
        subcategory='Naturais',
    )
    session.add(produto)
    await session.commit()

    result = await session.scalar(
        select(Produto).where(Produto.name == 'Suco de Maracujá')
    )

    assert result is not None
    assert result.image_url is None
    assert result.is_available is True  # Valor padrão


''' Testar quando integrarmos com mysql ou postgree
@pytest.mark.asyncio
async def test_create_produto_categoria_invalida(session):
    """Testa que não é possível criar produto com categoria inválida"""
    produto = Produto(
        name='Produto Invalido',
        price=100.00,
        category='categoria_invalida',  # Valor inválido
    )
    session.add(produto)

    with pytest.raises(Exception, match='categoria_invalida'):
        # SQLAlchemy lança erro no commit
        await session.commit()'''


@pytest.mark.asyncio
async def test_update_produto(session):
    """Testa atualização de um produto existente"""
    # Cria produto
    produto = Produto(
        name='Frango Grelhado',
        price=2500.00,
        category=CategoriaProduto.PRINCIPAL,
    )
    session.add(produto)
    await session.commit()

    # Atualiza produto
    produto.price = float(2800.00)
    produto.description = 'Acompanha salada e arroz'
    produto.is_available = False
    await session.commit()

    # Verifica atualização
    result = await session.scalar(select(Produto).where(Produto.id == 1))

    assert result.price == float(2800.00)
    assert result.description == 'Acompanha salada e arroz'
    assert result.is_available is False


@pytest.mark.asyncio
async def test_delete_produto(session):
    """Testa deleção de um produto"""
    produto = Produto(
        name='Produto para Deletar',
        price=100.00,
        category=CategoriaProduto.PETISCO,
    )
    session.add(produto)
    await session.commit()

    # Deleta produto
    await session.delete(produto)
    await session.commit()

    # Verifica se foi deletado
    result = await session.scalar(
        select(Produto).where(Produto.name == 'Produto para Deletar')
    )
    assert result is None


@pytest.mark.asyncio
async def test_listar_produtos_disponiveis(session):
    """Testa listagem apenas de produtos disponíveis"""
    # Cria produtos
    produtos = [
        Produto(
            name='Produto 1',
            price=100.00,
            category=CategoriaProduto.BEBIDA,
            is_available=True,
        ),
        Produto(
            name='Produto 2',
            price=200.00,
            category=CategoriaProduto.BEBIDA,
            is_available=False,
        ),
        Produto(
            name='Produto 3',
            price=300.00,
            category=CategoriaProduto.BEBIDA,
            is_available=True,
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()

    # Busca apenas disponíveis
    result = await session.scalars(select(Produto).where(Produto.is_available))
    produtos_disponiveis = result.all()

    assert len(produtos_disponiveis) == int(2)
    assert all(p.is_available is True for p in produtos_disponiveis)


@pytest.mark.asyncio
async def test_filtrar_produtos_por_categoria(session):
    """Testa filtro de produtos por categoria"""
    produtos = [
        Produto(
            name='Pizza', price=1500.00, category=CategoriaProduto.PRINCIPAL
        ),
        Produto(name='Suco', price=450.00, category=CategoriaProduto.SUCOS),
        Produto(
            name='Cerveja', price=380.00, category=CategoriaProduto.CERVEJA
        ),
        Produto(
            name='Lasanha', price=1800.00, category=CategoriaProduto.PRINCIPAL
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()

    # Busca apenas PRINCIPAL
    result = await session.scalars(
        select(Produto).where(Produto.category == CategoriaProduto.PRINCIPAL)
    )
    produtos_principal = result.all()

    assert len(produtos_principal) == int(2)
    assert all(
        p.category == CategoriaProduto.PRINCIPAL for p in produtos_principal
    )


@pytest.mark.asyncio
async def test_produto_sem_nome(session):
    """Testa que não é possível criar produto sem nome"""
    produto = Produto(
        name=None,  # name é NOT NULL
        price=100.00,
        category=CategoriaProduto.BEBIDA,
    )
    session.add(produto)

    with pytest.raises(IntegrityError):  # Só o commit gera o erro
        await session.commit()


@pytest.mark.asyncio
async def test_produto_sem_preco(session):
    """Testa que não é possível criar produto sem preço"""
    produto = Produto(
        name='Produto sem Preco',
        price=None,  # price é NOT NULL
        category=CategoriaProduto.BEBIDA,
    )
    session.add(produto)

    with pytest.raises(IntegrityError):  # Só o commit gera o erro
        await session.commit()


@pytest.mark.asyncio
async def test_produto_preco_zero(session):
    """Testa que produto pode ter
    preço zero (para testes ou brindes)"""
    produto = Produto(
        name='Brinde', price=0.00, category=CategoriaProduto.PETISCO
    )
    session.add(produto)
    await session.commit()

    result = await session.scalar(
        select(Produto).where(Produto.name == 'Brinde')
    )
    assert result.price == float(0.00)


@pytest.mark.asyncio
async def test_buscar_produto_por_public_id(session):
    """Testa busca de produto pelo public_id"""
    produto = Produto(
        name='Produto Busca', price=500.00, category=CategoriaProduto.CAFE
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    # Busca pelo public_id
    result = await session.scalar(
        select(Produto).where(Produto.public_id == produto.public_id)
    )
    assert result is not None
    assert result.id == produto.id
    assert result.name == 'Produto Busca'
