import pytest

from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_get_random(user_repo):
    await UserFactory.create_batch_in_repo(user_repo, size=3, commit_each=True)

    # choose one user random
    users = await user_repo.get_random()
    assert len(users) == int(1)

    # choose two users random
    users = await user_repo.get_random(limit=2)
    assert len(users) == int(2)


@pytest.mark.asyncio
async def test_get_latest(user_repo, user, other_user):
    user = await user_repo.get_latest(limit=1)
    assert len(user) == int(1)

    user = await user_repo.get_latest(limit=2)
    assert len(user) == int(2)
