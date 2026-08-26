from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from restaurante_api.app import app
from restaurante_api.core.database import get_session, table_registry
from restaurante_api.core.security import hash_password
from restaurante_api.models import CategoriaProduto, Produto
from restaurante_api.models.user import User
from restaurante_api.repositories.user import UserRepository
from restaurante_api.schemas.user import UserType

from .factories.user_factory import UserFactory


@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.drop_all)


@contextmanager
def _mock_db_time(*, model, time=datetime(2024, 1, 1)):
    def fake_time_hook(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time
        if hasattr(target, 'updated_at'):
            target.updated_at = time
        if hasattr(target, 'public_id'):
            target.public_id = '00000000-0000-0000-0000-000000000000'

    event.listen(model, 'before_insert', fake_time_hook)

    yield time

    event.remove(model, 'before_insert', fake_time_hook)


@pytest.fixture
def mock_db_time():
    return _mock_db_time


@pytest.fixture
def user_repo(session):
    return UserRepository(session)


@pytest_asyncio.fixture
async def user(user_repo):
    user_created = await UserFactory.create_in_repo(
        user_repo,
        username='testtest',
        email='testtest@gmail.com',
        password='123',
    )

    await user_repo.refresh(user_created)
    user_created.clean_password = '123'

    return user_created


@pytest_asyncio.fixture
async def other_user(user_repo):
    user_2 = await UserFactory.create_in_repo(
        user_repo, email='tazcmanongobulabula@gmail.com'
    )

    await user_repo.refresh(user_2)
    user.clean_password = '123'

    return user_2


@pytest_asyncio.fixture
async def admin_user(session):
    password = '123'
    user = User(
        username='admin',
        password=hash_password(password),
        email='admin@gmail.com',
        phone='11999999999',
        user_type=UserType.ADMIN,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    user.clean_password = password

    return user


@pytest.fixture
def token(client, user):
    response = client.post(
        'token/login',
        data={'username': user.email, 'password': user.clean_password},
    )

    return response.json()['access_token']


@pytest.fixture
def admin_token(client, admin_user):
    """Token de autenticação para admin"""
    response = client.post(
        'token/login', data={'username': admin_user.email, 'password': '123'}
    )
    return response.json()['access_token']


@contextmanager
def _mock_delete_attr(*, model, attributes_to_remove=None):
    """
    Mock para remover atributos específicos durante o 'before_insert'.

    Args:
        model: O modelo SQLAlchemy (ex: User, Contract)
        attributes_to_remove: Lista de nomes de atributos a serem removidos

    Exemplo:
        with mock_delete_attr(
            model=User, attributes_to_remove=['public_id', 'created_at']
        ):
            user = User(username="test")  # public_id desactivate
            session.add(user)
            await session.flush()
    """
    if attributes_to_remove is None:
        attributes_to_remove = []

    def fake_delete_attr_hook(mapper, connection, target):
        """Hook que remove os atributos especificados antes da inserção."""
        for attr_name in attributes_to_remove:
            if hasattr(target, attr_name):
                # Opção 1: Remove o atributo completamente
                delattr(target, attr_name)

                # Opção 2: Seta como None (alternativa)
                # setattr(target, attr_name, None)

    # Registra o evento
    event.listen(model, 'before_insert', fake_delete_attr_hook)

    try:
        yield
    finally:
        # Remove o evento após o uso
        event.remove(model, 'before_insert', fake_delete_attr_hook)


@pytest.fixture
def mock_delete_attr():
    """Fixture para usar o mock_delete_attr nos testes."""
    return _mock_delete_attr


@pytest.fixture
def mock_session():
    """Mock da sessão do banco."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


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
