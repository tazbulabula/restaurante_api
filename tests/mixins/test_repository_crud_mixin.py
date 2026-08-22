from typing import Any, Dict

import pytest

from restaurante_api.schemas.user import UserUpdate
from tests.factories.user_factory import UserFactory


# =================Tests of CRUD==================================
@pytest.mark.asyncio
async def test_create_user_with_repository(user_repo):
    dados = UserFactory()
    created_user = await user_repo.create(**dados.model_dump())
    await user_repo.commit()

    assert created_user.public_id is not None
    assert created_user.id is not None
    assert created_user.username is not None


@pytest.mark.asyncio
async def test_get_user_by_email_with_repository(user, user_repo):
    user_db = await user_repo.get_by_email(user.email)

    assert user_db == user


@pytest.mark.asyncio
async def test_get_user_by_id_with_repository(user, user_repo):
    user_db = await user_repo.get(user.id)

    assert user_db == user


@pytest.mark.asyncio
async def test_get_user_by_public_id_with_repository(user, user_repo):
    user_db = await user_repo.get_by_public_id(user.public_id)

    assert user_db == user


@pytest.mark.asyncio
async def test_update_user_with_repository(user, user_repo):
    user_update = UserUpdate(email='taz@gmail.com')
    user_db = await user_repo.update(
        user.public_id, **user_update.model_dump()
    )

    assert user_db.email == 'taz@gmail.com'


@pytest.mark.asyncio
async def test_update_user_none_args_with_repository(user, user_repo):
    user_db = await user_repo.update(user.public_id)

    assert user_db == user


"""
testar mais tarde.
@pytest.mark.asyncio
async def test_get_by_public_none(mock_delete_attr, user_repo):
    with mock_delete_attr(model=User, attributes_to_remove=['public_id']):
        dados = UserFactory()
        created_user = await user_repo.create(**dados.model_dump())
        await user_repo.commit()
        assert not hasattr(created_user, 'public_id')"""


@pytest.mark.asyncio
async def test_delete_user_with_repository(user, user_repo):
    user_db = await user_repo.delete(user.public_id)

    assert user_db is True


@pytest.mark.asyncio
async def test_create_from_dict(user_repo):
    """
    Testa o método create_from_dict que recebe um dicionário.
    """

    # 1. Dados em formato de dicionário
    user_data: Dict[str, Any] = {
        'username': 'joao_dict',
        'email': 'joao_dict@example.com',
        'password': 'hash_da_senha_123',
        'phone': '11999999999',
    }

    # 2. Executa o método create_from_dict
    user = await user_repo.create_from_dict(user_data)
    await user_repo.commit()

    # 3. Verificações
    assert user.id is not None
    assert user.username == 'joao_dict'
    assert user.email == 'joao_dict@example.com'
    assert user.phone == '11999999999'


@pytest.mark.asyncio
async def test_create_from_dict_with_missing_fields(user_repo):
    """
    Testa create_from_dict com dados incompletos.
    """

    incomplete_data = {
        'email': 'incompleto@example.com',
        'password': 'hash123',
    }

    # Testa que a criação lança exceção
    with pytest.raises(TypeError):
        await user_repo.create_from_dict(incomplete_data)

    # O commit não é necessário porque a criação falhou
    # A sessão deve ser limpa/rollback
    await user_repo.rollback()


@pytest.mark.asyncio
async def test_create_from_dict_batch(user_repo):
    """
    Testa create_from_dict com múltiplos dicionários (lote).
    """

    # Lista de dicionários
    users_data = [
        {
            'username': 'user_1',
            'email': 'user1@example.com',
            'password': 'hash1',
            'phone': '111111111',
        },
        {
            'username': 'user_2',
            'email': 'user2@example.com',
            'password': 'hash2',
            'phone': '222222222',
        },
        {
            'username': 'user_3',
            'email': 'user3@example.com',
            'password': 'hash3',
            'phone': '333333333',
        },
    ]

    # Cria todos os usuários
    created_users = []
    for data in users_data:
        user = await user_repo.create_from_dict(data)
        created_users.append(user)

    await user_repo.commit()

    # Verificações
    assert len(created_users) == int(3)
    assert created_users[0].username == 'user_1'
    assert created_users[1].username == 'user_2'
    assert created_users[2].username == 'user_3'


@pytest.mark.asyncio
async def test_create_from_dict_with_factory(user_repo):
    """
    Testa create_from_dict usando dados gerados pelo factory.
    """

    # Usa o factory para gerar os dados (dicionário)
    user_data = UserFactory.build(
        username='factory_dict', email='factory@example.com'
    )
    # UserFactory.build retorna UserCreate, precisamos converter para dict
    user_dict = user_data.model_dump()

    # Executa
    user = await user_repo.create_from_dict(user_dict)
    await user_repo.commit()

    # Verifica
    assert user.id is not None
    assert user.username == 'factory_dict'
    assert user.email == 'factory@example.com'


@pytest.mark.asyncio
async def test_create_from_dict_vs_create_comparison(user_repo):
    """
    Compara create_from_dict com create (devem produzir o mesmo resultado).
    """

    # Dados de teste
    username = 'comparison_user'
    email = 'comparison@example.com'
    password = 'hash_comparison'

    # Método 1: create (com kwargs)
    user_via_create = await user_repo.create(
        username=username,
        email=email,
        password=password,
        phone='999999999',
    )

    # Método 2: create_from_dict (com dicionário)
    user_dict = {
        'username': f'{username}_2',
        'email': 'comparison2@example.com',
        'password': password,
        'phone': '888888888',
    }
    user_via_dict = await user_repo.create_from_dict(user_dict)

    await user_repo.commit()

    # Ambos devem ter sido criados
    assert user_via_create.id is not None
    assert user_via_dict.id is not None
    assert user_via_create.username == username
    assert user_via_dict.username == f'{username}_2'


@pytest.mark.asyncio
async def test_create_from_schema(user_repo):
    """
    Testa create_from_schema que recebe um Pydantic BaseModel.
    """

    # 1. Cria um schema de criação de usuário
    user_create = UserFactory.build()

    # 2. Executa o método create_from_schema
    user = await user_repo.create_from_schema(user_create)
    await user_repo.commit()

    # 3. Verificações
    assert user.id is not None
    assert user.username == user_create.username
    assert user.email == user_create.email
