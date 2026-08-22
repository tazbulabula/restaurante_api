"""User Validations - Métodos de validação e verificação."""

from restaurante_api.models.user import UserType

from .base import UserBaseRepository


class UserValidationsMixin:
    """Mixin com métodos de validação."""

    async def email_exists(self, email: str) -> bool:
        return await self.exists(email=email)

    async def username_exists(self, username: str) -> bool:
        return await self.exists(username=username)

    async def is_supplier(self, public_id: str) -> bool:
        user = await self.get_by_public_id(public_id)
        return user is not None and user.user_type == UserType.SUPPLIER

    async def is_admin(self, public_id: str) -> bool:
        user = await self.get_by_public_id(public_id)
        users_types = [UserType.ADMIN]
        return user is not None and user.user_type in users_types

    async def can_upgrade_to_supplier(self, public_id: str) -> bool:
        user = await self.get_by_public_id(public_id)
        if not user or user.deleted_at is not None:
            return False
        return user.user_type == UserType.CLIENT


class UserValidationRepository(UserBaseRepository, UserValidationsMixin):
    """Repository focado em validações."""

    pass
