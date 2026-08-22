import pytest

from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_count(user_repo):
    # Create 5 users
    users = []
    for i in range(5):
        user = await UserFactory.create_in_repo(
            user_repo,
            commit=False,  # Não commita individualmente
            username=f'user_{i}',
            email=f'user_{i}@gmail.com',
        )
        users.append(user)
    await user_repo.commit()

    # Test count none filters
    total_count = await user_repo.count()
    assert total_count == int(5)
    filters = {'username': 'user_1'}
    total_count_with_filters = await user_repo.count(**filters)
    assert total_count_with_filters == int(1)

    users_db = await user_repo.get_all()

    assert len(users) == len(users_db)


@pytest.mark.asyncio
async def test_exist_user(user_repo):
    await UserFactory.create_in_repo(
        user_repo, username='Taz', email='taz@gmail.com', commit=False
    )
    await user_repo.commit()

    user_with_username = await user_repo.exists(username='Taz')

    assert user_with_username == int(1)


"""
Esse teste será feito quando eu ter uma coluna contável
@pytest.mark.asyncio
async def test_aggregate_sum(user_repo):
    await UserFactory.create_batch_in_repo(user_repo, size=5, commit_each=True)

    sum_ids = await user_repo.aggregate_sum(id)
    assert sum_ids == int(15)"""


"""@pytest.mark.asyncio
async def test_aggregate_min(user_repo):
    await UserFactory.create_batch_in_repo(user_repo, size=5, commit_each=True)
    min_number = await user_repo.aggregate_min('id')
    assert min_number == 1"""
