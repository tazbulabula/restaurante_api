import pytest

from restaurante_api.models.user import User, UserType
from restaurante_api.schemas.user import UserFilterSchema
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_query_get_all(user_repo, user, other_user):
    users = await user_repo.get_all()

    assert len(users) == int(2)


@pytest.mark.asyncio
async def test_query_with_order_by(user_repo, user, other_user):
    users_1 = await user_repo.get_all(order_by='created_at')

    assert len(users_1) == int(2)

    with pytest.raises(AttributeError):
        await user_repo.get_all(order_by='order_by')

    users_2 = await user_repo.get_all(order_by='id', descending=True)
    user_1 = users_2[0]

    assert len(users_2) == int(2)
    assert user_1.id == int(2)


@pytest.mark.asyncio
async def test_get_by_filters(user_repo, user, other_user):
    filters = UserFilterSchema(public_id=user.public_id)
    filters = filters.to_filters_dict()
    data = await user_repo.get_by_filters(**filters)

    assert data == user


@pytest.mark.asyncio
async def test_filter_by(user_repo, user, other_user):
    filters = UserFilterSchema(user_type=UserType.CLIENT)
    filters = filters.to_filters_dict()
    data = await user_repo.filter_by(**filters)

    assert len(data) == int(2)


@pytest.mark.asyncio
async def test_find_by_not_equal_operator(user_repo):
    """Testa operador de diferença (!=)."""

    # 1. Cria usuários normais (todos começam como CLIENT)
    await UserFactory.create_in_repo(user_repo, username='user1')
    await UserFactory.create_in_repo(user_repo, username='user2')
    user3 = await UserFactory.create_in_repo(user_repo, username='user3')

    # 2. Atualiza um deles para ADMIN (simulando aprovação)
    await user_repo.update(user3.public_id, user_type=UserType.ADMIN)

    await user_repo.commit()

    # 3. Busca usuários que NÃO são admin
    conditions = [(User.user_type, '!=', UserType.ADMIN)]
    results = await user_repo.find_by(conditions)

    # Deve retornar user1 e user2 (2 usuários)
    assert len(results) == int(2)
    for user in results:
        assert user.user_type != UserType.ADMIN
        assert user.user_type == UserType.CLIENT


@pytest.mark.asyncio
async def test_find_by_like_operator(user_repo):
    """Testa operador LIKE (case sensitive)."""
    await UserFactory.create_in_repo(user_repo, username='joao_silva')
    await UserFactory.create_in_repo(user_repo, username='maria_silva')
    await UserFactory.create_in_repo(user_repo, username='joao_santos')
    await user_repo.commit()

    # Busca usuários com username contendo "silva"
    conditions = [(User.username, 'like', '%silva%')]
    results = await user_repo.find_by(conditions)

    assert len(results) == int(2)
    assert all('silva' in user.username for user in results)


@pytest.mark.asyncio
async def test_find_by_ilike_operator(user_repo):
    """Testa operador ILIKE (case insensitive)."""
    await UserFactory.create_in_repo(user_repo, username='JoaoSilva')
    await UserFactory.create_in_repo(user_repo, username='mariaSILVA')
    await UserFactory.create_in_repo(user_repo, username='joaosantos')
    await user_repo.commit()

    # Busca usuários com username contendo "silva" (ignora case)
    conditions = [(User.username, 'ilike', '%silva%')]
    results = await user_repo.find_by(conditions)

    assert len(results) == int(2)
    assert all('silva' in user.username.lower() for user in results)


@pytest.mark.asyncio
async def test_find_by_in_operator(user_repo):
    """Testa operador IN."""
    await UserFactory.create_in_repo(user_repo, username='user1')
    await UserFactory.create_in_repo(user_repo, username='user2')
    await UserFactory.create_in_repo(user_repo, username='user3')
    await UserFactory.create_in_repo(user_repo, username='user4')
    await user_repo.commit()

    # Busca usuários com username em uma lista específica
    conditions = [(User.username, 'in', ['user1', 'user2', 'user5'])]
    results = await user_repo.find_by(conditions)

    assert len(results) == int(2)
    assert results[0].username in {'user1', 'user2'}
    assert results[1].username in {'user1', 'user2'}


@pytest.mark.asyncio
async def test_find_by_empty_conditions(user_repo):
    """Testa lista vazia de condições - deve retornar todos os registros."""
    # Cria alguns usuários
    await UserFactory.create_in_repo(user_repo, username='user1')
    await UserFactory.create_in_repo(user_repo, username='user2')
    await UserFactory.create_in_repo(user_repo, username='user3')
    await user_repo.commit()

    # Passa lista vazia
    results = await user_repo.find_by([])

    # Deve retornar todos os usuários (get_all)
    assert len(results) >= int(3)


@pytest.mark.asyncio
async def test_find_by_no_results(user_repo):
    """Testa quando nenhum registro corresponde aos filtros."""
    await UserFactory.create_in_repo(user_repo, username='joao', age=25)
    await user_repo.commit()

    # Busca por condição que não existe
    conditions = [(User.username, '==', 'inexistente')]
    results = await user_repo.find_by(conditions)

    assert len(results) == int(0)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_find_by_invalid_operator(user_repo):
    """Testa operador inválido - deve levantar ValueError."""
    # Cria um usuário
    await UserFactory.create_in_repo(user_repo, username='joao')
    await user_repo.commit()

    # Tenta usar operador inválido
    conditions = [(User.username, 'invalid_operator', 'joao')]

    with pytest.raises(ValueError, match='Operador não suportado'):
        await user_repo.find_by(conditions)


@pytest.mark.asyncio
async def test_search(user_repo):
    """Testa método search com filtros e ordenação."""
    await UserFactory.create_in_repo(user_repo, username='joao_silva')
    await UserFactory.create_in_repo(user_repo, username='maria_silva')
    await UserFactory.create_in_repo(user_repo, username='joao_santos')
    await user_repo.commit()

    # com filtro none
    with pytest.raises(
        ValueError, match='At least one field must be provided'
    ):
        await user_repo.search(search_term='silva', fields=None)

    # Busca por "silva" e ordena por created_at desc
    filters = ['username']

    # with case sensitive
    results = await user_repo.search(
        search_term='silva', fields=filters, case_sensitive=True
    )

    assert len(results) == int(2)
    assert all('silva' in user.username for user in results)

    # None case sensitive
    results_1 = await user_repo.search(search_term='silva', fields=filters)

    assert len(results_1) == int(2)
    assert all('silva' in user.username for user in results_1)
