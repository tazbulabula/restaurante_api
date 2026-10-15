# tests/routes/test_produtos.py

import io
from http import HTTPStatus

import pytest
from sqlalchemy import select

from restaurante_api.core.settings import settings
from restaurante_api.models.produto import CategoriaProduto, Produto


def _fake_image_bytes(size_bytes: int = 1024) -> bytes:
    """Gera bytes pseudo-imagem para testes."""
    return b'\xff\xd8\xff\xe0' + b'\x00' * (size_bytes - 4)


def _image_file(
    filename: str = 'foto.jpg', size_bytes: int = 1024
) -> tuple[str, io.BytesIO, str]:
    """Devolve tuple pronta para `files=` do httpx."""
    return (filename, io.BytesIO(_fake_image_bytes(size_bytes)), 'image/jpeg')


@pytest.mark.asyncio
async def test_listar_produtos(client, session):
    """Testa listagem de produtos"""
    produtos = [
        Produto(
            name='Produto 1', price=100.00, category=CategoriaProduto.BEBIDA
        ),
        Produto(
            name='Produto 2', price=200.00, category=CategoriaProduto.BEBIDA
        ),
        Produto(
            name='Produto 3', price=300.00, category=CategoriaProduto.PRINCIPAL
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()

    response = client.get('/produtos/listar')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(3)
    assert data[0]['name'] == 'Produto 1'
    assert data[1]['name'] == 'Produto 2'
    assert data[2]['name'] == 'Produto 3'


@pytest.mark.asyncio
async def test_listar_produtos_com_filtro_categoria(client, session):
    """Testa listagem filtrando por categoria"""
    produtos = [
        Produto(
            name='Pizza', price=1500.00, category=CategoriaProduto.PRINCIPAL
        ),
        Produto(name='Suco', price=450.00, category=CategoriaProduto.SUCOS),
        Produto(
            name='Cerveja', price=380.00, category=CategoriaProduto.CERVEJA
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()

    response = client.get('/produtos/listar?categoria=principal')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['name'] == 'Pizza'
    assert data[0]['category'] == 'principal'


@pytest.mark.asyncio
async def test_listar_produtos_filtro_disponibilidade(client, session):
    """Testa listagem filtrando por disponibilidade"""
    produtos = [
        Produto(
            name='Disponível',
            price=100.00,
            category=CategoriaProduto.BEBIDA,
            is_available=True,
        ),
        Produto(
            name='Indisponível',
            price=200.00,
            category=CategoriaProduto.BEBIDA,
            is_available=False,
        ),
    ]
    for p in produtos:
        session.add(p)
    await session.commit()

    response = client.get('/produtos/listar?disponivel=true')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['name'] == 'Disponível'
    assert data[0]['is_available'] is True


@pytest.mark.asyncio
async def test_listar_produtos_paginacao(client, session):
    """Testa paginação na listagem"""
    for i in range(10):
        produto = Produto(
            name=f'Produto {i}',
            price=100.00 + i,
            category=CategoriaProduto.BEBIDA,
        )
        session.add(produto)
    await session.commit()

    response = client.get('/produtos/listar?limit=3&offset=2')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(3)
    assert data[0]['name'] == 'Produto 2'
    assert data[1]['name'] == 'Produto 3'
    assert data[2]['name'] == 'Produto 4'


@pytest.mark.asyncio
async def test_buscar_produto_por_public_id(client, session):
    """Testa busca de produto pelo public_id"""
    produto = Produto(
        name='Produto Busca', price=500.00, category=CategoriaProduto.CAFE
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.get(f'/produtos/public/{produto.public_id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['name'] == 'Produto Busca'
    assert data['public_id'] == produto.public_id


@pytest.mark.asyncio
async def test_buscar_produto_public_id_nao_encontrado(client):
    """Testa busca de produto com public_id inexistente"""
    response = client.get(
        '/produtos/public/00000000-0000-0000-0000-000000000000'
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_produto(client, session, admin_token):
    """Testa criação de produto (admin) com upload de imagem"""
    form_data = {
        'name': 'Pizza Margherita',
        'description': 'Mussarela, tomate e manjericão',
        'price': '2500.00',
        'category': 'principal',
        'subcategory': 'Massas',
        'is_available': 'true',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
        files={'image': _image_file('pizza.jpg')},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Pizza Margherita'
    assert data['price'] == float(2500.00)
    assert data['category'] == 'principal'
    assert data['public_id'] is not None
    assert data['image_url'] is not None
    assert data['image_url'].startswith('/static/produtos/')
    assert data['image_url'].endswith('.jpg')

    # Confirma no banco
    result = await session.execute(
        select(Produto).where(Produto.name == 'Pizza Margherita')
    )
    produto = result.scalar_one()
    assert produto.price == float(2500.00)

    # Confirma que o ficheiro foi gravado
    nome_ficheiro = data['image_url'].split('/')[-1]
    caminho = settings.products_upload_path / nome_ficheiro
    assert caminho.is_file()

    # Cleanup
    caminho.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_criar_produto_sem_imagem(client, session, admin_token):
    """Testa criação de produto sem imagem (image_url fica None)"""
    form_data = {
        'name': 'Produto Sem Imagem',
        'price': '100.00',
        'category': 'bebida',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['image_url'] is None


@pytest.mark.asyncio
async def test_criar_produto_sem_autenticacao(client):
    """Testa criação de produto sem token (deve falhar)"""
    produto_data = {
        'name': 'Produto Sem Auth',
        'price': 100.00,
        'category': 'principal',
    }

    response = client.post('/produtos/create', json=produto_data)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert 'Not authenticated' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_produto_usuario_comum(client, token):
    """Testa criação de produto com usuário comum (deve falhar)"""
    form_data = {
        'name': 'Produto Usuario Comum',
        'price': '100.00',
        'category': 'principal',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {token}'},
        data=form_data,
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_criar_produto_nome_duplicado(client, session, admin_token):
    """Testa criação de produto com nome já existente"""
    produto = Produto(
        name='Produto Duplicado',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
    )
    session.add(produto)
    await session.commit()

    form_data = {
        'name': 'Produto Duplicado',
        'price': '200.00',
        'category': 'bebida',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'já existe' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_produto_categoria_invalida(client, admin_token):
    """Testa criação de produto com categoria inválida"""
    form_data = {
        'name': 'Produto Invalido',
        'price': '100.00',
        'category': 'categoria_invalida',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_criar_produto_preco_negativo(client, admin_token):
    """Testa criação de produto com preço negativo"""
    form_data = {
        'name': 'Produto Errado',
        'price': '-100.00',
        'category': 'bebida',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'price' in str(response.json())


@pytest.mark.asyncio
async def test_atualizar_produto(client, session, admin_token):
    """Testa atualização de produto (admin)"""
    produto = Produto(
        name='Produto Antigo', price=100.00, category=CategoriaProduto.BEBIDA
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    update_data = {
        'name': 'Produto Atualizado',
        'price': 150.00,
        'description': 'Nova descrição',
    }

    response = client.put(
        f'/produtos/update/{produto.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=update_data,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['name'] == 'Produto Atualizado'
    assert data['price'] == float(150.00)
    assert data['description'] == 'Nova descrição'


@pytest.mark.asyncio
async def test_atualizar_produto_usuario_comum(client, session, token):
    """Testa atualização de produto com usuário comum (deve falhar)"""
    produto = Produto(
        name='Produto Teste', price=100.00, category=CategoriaProduto.BEBIDA
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.put(
        f'/produtos/update/{produto.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'price': 200.00},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_atualizar_produto_parcial(client, session, admin_token):
    """Testa atualização parcial de produto"""
    produto = Produto(
        name='Produto Teste',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
        description='Descrição original',
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.put(
        f'/produtos/update/{produto.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'price': 200.00},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['name'] == 'Produto Teste'
    assert data['price'] == float(200.00)
    assert data['description'] == 'Descrição original'


@pytest.mark.asyncio
async def test_atualizar_produto_nao_encontrado(client, admin_token):
    """Testa atualização de produto inexistente"""
    response = client.put(
        '/produtos/update/999',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'name': 'Novo Nome'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_deletar_produto(client, session, admin_token):
    """Testa deleção de produto (admin)"""
    produto = Produto(
        name='Produto para Deletar',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.delete(
        f'/produtos/delete/{produto.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT

    result = await session.execute(
        select(Produto).where(Produto.id == produto.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_deletar_produto_usuario_comum(client, session, token):
    """Testa deleção de produto com usuário comum (deve falhar)"""
    produto = Produto(
        name='Produto Teste',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.delete(
        f'/produtos/delete/{produto.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_deletar_produto_nao_encontrado(client, admin_token):
    """Testa deleção de produto inexistente"""
    response = client.delete(
        '/produtos/delete/999',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_alternar_disponibilidade(client, session, admin_token):
    """Testa alternância de disponibilidade (admin)"""
    produto = Produto(
        name='Produto Teste',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
        is_available=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.patch(
        f'/produtos/{produto.public_id}/disponibilidade?disponivel=false',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['is_available'] is False
    assert data['public_id'] == produto.public_id

    response = client.patch(
        f'/produtos/{produto.public_id}/disponibilidade?disponivel=true',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['is_available'] is True


@pytest.mark.asyncio
async def test_alternar_disponibilidade_usuario_comum(client, session, token):
    """Testa alternância de disponibilidade com usuário comum (deve falhar)"""
    produto = Produto(
        name='Produto Teste',
        price=100.00,
        category=CategoriaProduto.BEBIDA,
        is_available=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.patch(
        f'/produtos/{produto.public_id}/disponibilidade?disponivel=false',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_alternar_disponibilidade_produto_nao_encontrado(
    client, admin_token
):
    """Testa alternância de disponibilidade de produto inexistente"""
    response = client.patch(
        '/produtos/999/disponibilidade?disponivel=false',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrado' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_produto_extensao_invalida(client, admin_token):
    """Testa upload com extensão não permitida"""
    form_data = {
        'name': 'Produto Ext Ruim',
        'price': '100.00',
        'category': 'bebida',
    }

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
        files={
            'image': (
                'virus.exe',
                io.BytesIO(b'MZ\x00\x00'),
                'application/octet-stream',
            )
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'não permitida' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_produto_imagem_grande(client, admin_token, monkeypatch):
    """Testa upload de imagem acima do tamanho máximo"""
    monkeypatch.setattr(settings, 'MAX_UPLOAD_SIZE_MB', 1)

    form_data = {
        'name': 'Produto Grande',
        'price': '100.00',
        'category': 'bebida',
    }

    grande = _image_file('grande.jpg', size_bytes=2 * 1024 * 1024)

    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
        files={'image': grande},
    )

    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert 'demasiado grande' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_atualizar_imagem_produto(client, session, admin_token):
    """Testa PATCH /produtos/{public_id}/imagem"""
    produto = Produto(
        name='Produto Imagem', price=100.00, category=CategoriaProduto.BEBIDA
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)

    response = client.patch(
        f'/produtos/{produto.public_id}/imagem',
        headers={'Authorization': f'Bearer {admin_token}'},
        files={'image': _image_file('nova.png')},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['image_url'] is not None
    assert data['image_url'].endswith('.png')

    # Cleanup
    nome = data['image_url'].split('/')[-1]
    (settings.products_upload_path / nome).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_imagem_servida_estaticamente(client, session, admin_token):
    """Verifica que a imagem fica acessível via /static/"""
    form_data = {
        'name': 'Produto Estático',
        'price': '100.00',
        'category': 'bebida',
    }
    response = client.post(
        '/produtos/create',
        headers={'Authorization': f'Bearer {admin_token}'},
        data=form_data,
        files={'image': _image_file('servida.jpg')},
    )
    assert response.status_code == HTTPStatus.CREATED
    url = response.json()['image_url']

    # httpx TestClient segue o mesmo `app`, então o mount /static funciona
    r = client.get(url)
    assert r.status_code == HTTPStatus.OK
    assert len(r.content) > 0

    # Cleanup
    nome = url.split('/')[-1]
    (settings.products_upload_path / nome).unlink(missing_ok=True)
