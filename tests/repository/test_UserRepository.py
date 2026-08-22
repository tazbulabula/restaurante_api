from datetime import datetime, timedelta, timezone

import pytest

from restaurante_api.schemas.user import UserType
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_delete_by_email(user_repo, user):
    user = await user_repo.delete_by_email(user.email)

    assert user is True

    user = await user_repo.delete_by_email('email_inexistente@gmail.com')

    assert user is False


@pytest.mark.asyncio
async def test_get_by_username_repository(user_repo, user):
    user_1 = await user_repo.get_by_username(username=user.username)

    assert user_1.email == user.email
    assert user_1.username == user.username


@pytest.mark.asyncio
async def test_get_by_user_type_repository(user_repo, user):
    users = await user_repo.get_by_user_type(user_type=UserType.CLIENT)

    assert len(users) == int(1)


@pytest.mark.asyncio
async def test_get_by_public_id_repository(user_repo, user):
    user_found = await user_repo.get_by_public_id(user.public_id)

    assert user_found.email == user.email


@pytest.mark.asyncio
async def test_get_clients_repository(user_repo):
    user_client = await UserFactory.create_in_repo(
        user_repo,
    )

    client = await user_repo.get_clients()
    client = client[0]

    client_general = await user_repo.get_clients(active_only=False)
    assert user_client.user_type == UserType.CLIENT
    assert client.user_type == UserType.CLIENT

    assert len(client_general) == int(1)


@pytest.mark.asyncio
async def test_get_admins_repository(user_repo, admin_user):
    admins_actives = await user_repo.get_admins()
    admin = admins_actives[0]

    admins_general = await user_repo.get_admins(active_only=False)

    assert len(admins_actives) == int(1)
    assert admin.user_type == UserType.ADMIN

    assert len(admins_general) == int(1)


@pytest.mark.asyncio
async def test_active_users_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.get_active_users()

    assert len(users) == int(3)


@pytest.mark.asyncio
async def test_search_users_with_username_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.search_users(search_term=user.username)

    assert len(users) == int(1)


@pytest.mark.asyncio
async def test_search_users_with_email_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.search_users(search_term=admin_user.email)

    assert len(users) == int(1)


@pytest.mark.asyncio
async def test_search_users_with_phone_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.search_users(search_term=other_user.phone)

    assert len(users) == int(1)


@pytest.mark.asyncio
async def test_get_recent_users_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.get_recent_users()

    assert len(users) == int(3)


@pytest.mark.asyncio
async def test_get_users_created_between_repository(
    user_repo, admin_user, user, other_user
):
    users = await user_repo.get_users_created_between(
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        end_date=datetime.now(),
    )

    assert len(users) == int(3)


@pytest.mark.asyncio
async def test_transactions_of_user_repository(user_repo, user):

    assert user.user_type == UserType.CLIENT

    admin = await user_repo.upgrade_to_admin(user.public_id)

    assert admin.user_type == UserType.ADMIN


@pytest.mark.asyncio
async def test_validations_users(user_repo, user, admin_user, other_user):

    email = await user_repo.email_exists(user.email)
    username = await user_repo.username_exists(user.username)

    assert email == bool(True)
    assert username == bool(True)

    admin = await user_repo.is_admin(admin_user.public_id)

    assert admin == bool(True)

    await user_repo.soft_delete(other_user.public_id)
