import pytest

from restaurante_api.models.user import UserType
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_bulk_create(user_repo):
    data = []

    for n in range(5):
        user = UserFactory.create()
        data.append(user.model_dump())

    data_db = await user_repo.bulk_create(data)
    assert len(data_db) == len(data)
    assert len(data_db) == int(5)


@pytest.mark.asyncio
async def test_bulk_update(user_repo, user, other_user):
    data = [
        (f'{user.public_id}', {'user_type': UserType.ADMIN}),
        (f'{other_user.public_id}', {'user_type': UserType.ADMIN}),
    ]
    data_db = await user_repo.bulk_update(data)
    assert len(data_db) == len(data)


@pytest.mark.asyncio
async def test_bulk_delete_all(user_repo, user):
    data = await user_repo.delete_all()
    assert data == int(1)


@pytest.mark.asyncio
async def test_chunked_create(user_repo):
    data = []

    for n in range(5):
        user = UserFactory.create()
        data.append(user.model_dump())

    data_db = await user_repo.chunked_create(data, chunk_size=1)
    assert len(data_db) == len(data)
    assert len(data_db) == int(5)


@pytest.mark.asyncio
async def test_bulk_chunked_update(user_repo, user, other_user):
    data = [
        (f'{user.public_id}', {'user_type': UserType.ADMIN}),
        (f'{other_user.public_id}', {'user_type': UserType.ADMIN}),
    ]
    data_db = await user_repo.chunked_update(data, chunk_size=20)
    assert len(data_db) == len(data)
