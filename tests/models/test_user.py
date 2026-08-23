from dataclasses import asdict

import pytest
from sqlalchemy import select

from restaurante_api.models.user import User
from restaurante_api.schemas.user import UserType


@pytest.mark.asyncio
async def test_create_user(session, mock_db_time):
    with mock_db_time(model=User) as time:
        new_user = User(
            username='Taz',
            password='1234',
            email='taz@gmail.com',
            phone='+244921351606',
        )
        session.add(new_user)
        await session.commit()

    user = await session.scalar(select(User).where(User.username == 'Taz'))

    assert asdict(user) == {
        'id': 1,
        'public_id': '00000000-0000-0000-0000-000000000000',
        'username': 'Taz',
        'email': 'taz@gmail.com',
        'password': '1234',
        'phone': '+244921351606',
        'user_type': UserType.CLIENT,
        'created_at': time,
        'updated_at': time,
        'deleted_at': None,
        'reservas': [],
        'pedidos': [],
    }
