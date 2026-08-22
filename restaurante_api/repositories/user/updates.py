"""User Updates - Métodos especializados de atualização."""

from datetime import datetime, timezone
from typing import Optional

from restaurante_api.models.user import User, UserType

from .base import UserBaseRepository


class UserUpdatesMixin:
    """Mixin com métodos de atualização especializados."""

    async def update_user_type(
        self, public_id: str, new_type: UserType
    ) -> Optional[User]:
        return await self.update(public_id, user_type=new_type)

    async def upgrade_to_admin(self, public_id: str) -> Optional[User]:
        return await self.update_user_type(public_id, UserType.ADMIN)

    async def update_last_login(self, public_id: str) -> Optional[User]:
        return await self.update(
            public_id, last_login=datetime.now(timezone.utc)
        )

    async def update_password(
        self, public_id: str, hashed_password: str
    ) -> Optional[User]:
        return await self.update(public_id, password=hashed_password)


class UserUpdateRepository(UserBaseRepository, UserUpdatesMixin):
    """Repository focado em operações de atualização."""

    pass
