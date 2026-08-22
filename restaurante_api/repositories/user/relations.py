"""User Relations - Métodos que carregam relacionamentos."""

from typing import List, Optional

from restaurante_api.models.user import User, UserType

from .base import UserBaseRepository


class UserRelationsMixin:
    """Mixin com métodos que carregam relacionamentos."""

    async def get_with_contracts(self, public_id: str) -> Optional[User]:
        return await self.get_with_relations(
            public_id, relations=['contracts']
        )

    async def get_with_store(self, public_id: str) -> Optional[User]:
        return await self.get_with_relations(public_id, relations=['store'])

    async def get_with_orders(self, public_id: str) -> Optional[User]:
        return await self.get_with_relations(public_id, relations=['orders'])

    async def get_with_all_relations(self, public_id: str) -> Optional[User]:
        return await self.get_with_relations(
            public_id, relations=['contracts', 'store', 'orders']
        )

    async def get_suppliers_with_stores(self) -> List[User]:
        return await self.get_all_with_relations(
            relations=['store'], user_type=UserType.SUPPLIER, deleted_at=None
        )


class UserRelationRepository(UserBaseRepository, UserRelationsMixin):
    """Repository focado em relacionamentos."""

    pass
