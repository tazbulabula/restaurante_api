# tests/test_user_factory.py
import pytest

from restaurante_api.repositories.user import UserRepository
from restaurante_api.schemas.user import UserCreate
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_factory_simple(session):
    user_repo = UserRepository(session)

    # 1. Gerar dados sem persistir (método nativo)
    user_data = UserFactory.build()
    assert isinstance(user_data, UserCreate)
    assert 'username' in user_data.model_dump()
    assert 'password' in user_data.model_dump()

    # 2. Gerar lote de dicionários (método nativo build_batch)
    users_data = UserFactory.build_batch(10)
    assert len(users_data) == int(10)

    # 3. Criar e persistir 1 usuário
    user = await UserFactory.create_in_repo(user_repo)
    assert user.id is not None

    # 4. Criar e persistir com dados customizados
    user = await UserFactory.create_in_repo(
        user_repo, username='Taz', email='taz@exemplo.com'
    )
    assert user.username == 'Taz'

    # 5. Criar lote de 20 usuários
    users = []
    for i in range(20):
        user = await UserFactory.create_in_repo(
            user_repo,
            commit=False,  # Não commita individualmente
            username=f'batch_user_{i}',
        )
        users.append(user)
    await user_repo.commit()  # Commit único no final

    assert len(users) == int(20)
    assert users[0].username == 'batch_user_0'
    assert users[19].username == 'batch_user_19'


@pytest.mark.asyncio
async def test_factory_batch_with_single_commit(user_repo):
    """Cria lote com commit único (mais eficiente)."""

    # Gera 50 usuários sem commit individual
    users = []
    for _ in range(50):
        user = await UserFactory.create_in_repo(user_repo, commit=False)
        users.append(user)

    # Commit único no final
    await user_repo.commit()

    assert len(users) == int(50)
    assert all(u.id for u in users)
