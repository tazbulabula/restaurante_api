# restaurante_api/services/user_services.py

from typing import List, Optional

from restaurante_api.core.security import hash_password
from restaurante_api.core.settings import settings
from restaurante_api.models.user import UserType
from restaurante_api.repositories.user import UserRepository
from restaurante_api.schemas.user import (
    UserCreate,
    UserFilterSchema,
    UserList,
    UserPublic,
    UserUpdate,
)
from restaurante_api.services.email_service import EmailService


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
    ):
        self.email_service = email_service
        self.user_repo = user_repo

    # ============================================================
    # MÉTODOS EXISTENTES
    # ============================================================

    async def register_user(self, user_create: UserCreate):
        # Verifica se email já existe
        if await self.user_repo.email_exists(user_create.email):
            raise ValueError('Esse Email está sendo usado por outro User.')

        if await self.user_repo.username_exists(user_create.username):
            raise ValueError('Este nome já existe.')

        # Cria usuário
        user = await self.user_repo.create(
            email=user_create.email,
            username=user_create.username,
            password=hash_password(user_create.password),
            phone=user_create.phone,
        )
        await self.user_repo.session.commit()

        # Envia email de boas-vindas
        if settings.ENVIRONMENT != "production":
            try:
                await self.email_service.send_welcome_email(
                    to_email=user.email, name=user.username
                )
            except Exception as e:
                print(f'Erro ao enviar email de boas-vindas: {e}')

        return user

    async def updated_user(self, public_id, data: UserUpdate):
        update_user = data.model_dump(exclude_unset=True)
        password = update_user.get('password')
        if 'password' in update_user:
            del update_user['password']

        if update_user.get('email'):
            existing = await self.user_repo.get_by_email(update_user['email'])
            if existing and existing.public_id != public_id:
                raise ValueError('Email already in use by another user')

        if not update_user:
            return await self.user_repo.get_by_public_id(public_id)

        if password:
            await self.user_repo.update_password(
                public_id=public_id, hashed_password=password
            )

        user = await self.user_repo.update(public_id, **update_user)
        await self.user_repo.session.commit()

        return user

    async def desactive_user(self, public_id):
        """Deprecated: use soft_delete_user"""
        user = await self.soft_delete_user(public_id)
        await self.user_repo.session.commit()
        return user

    async def delete_user(self, public_id):
        """Deprecated: use hard_delete_user"""
        user = await self.hard_delete_user(public_id)
        await self.user_repo.session.commit()
        return user

    # ============================================================
    # SOFT DELETE - MÉTODOS COMPLETOS
    # ============================================================

    async def soft_delete_user(self, public_id: str) -> Optional[UserPublic]:
        """Soft delete: marca o usuário como deletado"""
        user = await self.user_repo.soft_delete(public_id)
        if not user:
            return None

        return UserPublic(
            public_id=user.public_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type.value,
            is_active=user.deleted_at is None,
            deleted_at=user.deleted_at,
        )

    async def restore_user(self, public_id: str) -> Optional[UserPublic]:
        """Restaura um usuário deletado"""
        user = await self.user_repo.restore(public_id)

        if not user:
            return None

        new_user = UserPublic(
            public_id=user.public_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type.value,
            is_active=user.deleted_at is None,
            deleted_at=user.deleted_at,
        )

        return new_user

    async def hard_delete_user(self, public_id: str) -> bool:
        """Remove permanentemente um usuário do banco"""
        return await self.user_repo.hard_delete(public_id)

    async def get_deleted_users(self) -> List[UserPublic]:
        """Lista apenas usuários deletados"""
        users = await self.user_repo.get_deleted_users()
        return [
            UserPublic(
                public_id=user.public_id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                user_type=user.user_type.value,
                is_active=user.deleted_at is None,
                deleted_at=user.deleted_at,
            )
            for user in users
        ]

    # ============================================================
    # MÉTODOS DE LISTAGEM (ATUALIZADOS)
    # ============================================================

    async def list_users(
        self,
        filters: UserFilterSchema,
    ) -> UserList:
        """
        Lista todos os usuários com filtros (apenas admin).
        """

        users = await self.user_repo.get_all_users(
            search=filters.search,
            user_type=filters.user_type,
            include_deleted=filters.include_deleted or False,
            limit=filters.limit,
            offset=filters.offset,
        )

        total = await self.user_repo.count_users(
            search=filters.search,
            user_type=filters.user_type,
            include_deleted=filters.include_deleted or False,
        )

        users_public = [
            UserPublic(
                public_id=user.public_id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                user_type=user.user_type.value,
                is_active=user.deleted_at is None,
                deleted_at=user.deleted_at,
            )
            for user in users
        ]

        return UserList(
            users=users_public,
            total=total,
            page=(filters.offset // filters.limit) + 1,
            per_page=filters.limit,
        )

    async def get_user_by_public_id(
        self,
        public_id: str,
        include_deleted: bool = False,
    ) -> Optional[UserPublic]:
        """Busca um usuário pelo public_id"""
        user = await self.user_repo.get_by_public_id(
            public_id,
        )
        if not user:
            return None

        return UserPublic(
            public_id=user.public_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type.value,
            is_active=user.deleted_at is None,
            deleted_at=user.deleted_at,
        )

    async def change_user_type(
        self, public_id: str, new_type: str
    ) -> Optional[UserPublic]:
        """Altera o tipo de usuário (admin/client)"""
        user = await self.user_repo.get_by_public_id(public_id)
        if not user:
            return None

        user.user_type = UserType(new_type)
        await self.user_repo.session.commit()
        await self.user_repo.session.refresh(user)

        return UserPublic(
            public_id=user.public_id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type.value,
            is_active=user.deleted_at is None,
            deleted_at=user.deleted_at,
        )
