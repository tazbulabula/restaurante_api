"""User Queries - Métodos especializados de busca."""

from datetime import datetime
from typing import List, Optional

from restaurante_api.models.user import User, UserType

from .base import UserBaseRepository


class UserQueriesMixin:
    """Mixin com métodos de busca especializados."""

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.get_by_filters(email=email)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.get_by_filters(username=username)

    async def get_by_user_type(self, user_type: UserType) -> List[User]:
        return await self.filter_by(user_type=user_type)

    async def get_by_public_id(self, public_id: str) -> Optional[User]:
        """
        Busca usuário por public_id (UUID).

        Exemplo:
            user = await user_repo.get_by_public_id("abc-123-def")
        """
        return await super().get_by_public_id(public_id)

    async def get_suppliers(self, active_only: bool = True) -> List[User]:
        if active_only:
            return await self.filter_by(
                user_type=UserType.SUPPLIER, deleted_at=None
            )
        return await self.filter_by(user_type=UserType.SUPPLIER)

    async def get_clients(self, active_only: bool = True) -> List[User]:
        if active_only:
            return await self.filter_by(
                user_type=UserType.CLIENT, deleted_at=None
            )
        return await self.filter_by(user_type=UserType.CLIENT)

    async def get_admins(self, active_only: bool = True) -> List[User]:
        if active_only:
            return await self.filter_by(
                user_type=UserType.ADMIN, deleted_at=None
            )
        return await self.filter_by(user_type=UserType.ADMIN)

    async def get_active_users(self) -> List[User]:
        return await self.filter_by(deleted_at=None)

    async def search_users(
        self, search_term: str, case_sensitive: bool = False
    ) -> List[User]:
        return await self.search(
            search_term=search_term,
            fields=['username', 'email', 'phone'],
            case_sensitive=case_sensitive,
        )

    async def get_recent_users(self, limit: int = 10) -> List[User]:
        return await self.get_latest(limit=limit)

    async def get_users_created_between(
        self, start_date: datetime, end_date: datetime
    ) -> List[User]:
        return await self.find_by([
            (User.created_at, '>=', start_date),
            (User.created_at, '<=', end_date),
        ])


class UserQueryRepository(UserBaseRepository, UserQueriesMixin):
    """Repository focado em operações de consulta."""

    pass
