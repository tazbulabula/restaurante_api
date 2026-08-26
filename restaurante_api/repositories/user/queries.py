# restaurante_api/repositories/queries.py

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select

from restaurante_api.models.user import User, UserType
from restaurante_api.repositories.mixins import (
    BaseMixin,  # ✅ Importar BaseMixin
)
from restaurante_api.repositories.user import UserBaseRepository


class UserQueriesMixin(BaseMixin):  # ✅ Herdar de BaseMixin
    """Mixin com métodos de busca especializados com soft delete."""

    # ============================================================
    # MÉTODOS DE BUSCA BÁSICOS
    # ============================================================

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.get_by_filters(email=email)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.get_by_filters(username=username)

    async def get_by_user_type(self, user_type: UserType) -> List[User]:
        return await self.filter_by(user_type=user_type)

    async def get_by_public_id(
        self,
        public_id: str,
        include_deleted: bool = False,
    ) -> Optional[User]:
        """Busca usuário por public_id (UUID)."""
        query = select(User).where(User.public_id == public_id)
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

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
        """Lista apenas usuários ativos (não deletados)"""
        return await self.filter_by(deleted_at=None)

    async def get_deleted_users(self) -> List[User]:
        """Lista apenas usuários deletados"""
        query = select(User).where(User.deleted_at.is_not(None))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_deleted_by_public_id(self, public_id: str) -> Optional[User]:
        """Busca um usuário deletado pelo public_id"""
        query = select(User).where(
            and_(
                User.public_id == public_id,
                User.deleted_at.is_not(None),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def search_users(
        self,
        search_term: str,
        case_sensitive: bool = False,
        include_deleted: bool = False,
    ) -> List[User]:
        """Busca usuários por termo de pesquisa"""
        query = self.search_query(
            search_term=search_term,
            fields=['username', 'email', 'phone'],
            case_sensitive=case_sensitive,
        )
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_recent_users(self, limit: int = 10) -> List[User]:
        return await self.get_latest(limit=limit)

    async def get_users_created_between(
        self, start_date: datetime, end_date: datetime
    ) -> List[User]:
        return await self.find_by([
            (User.created_at, '>=', start_date),
            (User.created_at, '<=', end_date),
        ])

    # ============================================================
    # NOVOS MÉTODOS COM SOFT DELETE
    # ============================================================

    async def get_all_users(
        self,
        search: Optional[str] = None,
        user_type: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        """Lista todos os usuários com filtros opcionais."""
        query = select(User)

        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))

        if search:
            query = query.where(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                )
            )

        if user_type:
            if user_type == 'admin':
                query = query.where(User.user_type == UserType.ADMIN)
            elif user_type == 'client':
                query = query.where(User.user_type == UserType.CLIENT)

        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def count_users(
        self,
        search: Optional[str] = None,
        user_type: Optional[str] = None,
        include_deleted: bool = False,
    ) -> int:
        """Conta o total de usuários com os filtros aplicados"""
        query = select(func.count()).select_from(User)

        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))

        if search:
            query = query.where(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                )
            )

        if user_type:
            if user_type == 'admin':
                query = query.where(User.user_type == UserType.ADMIN)
            elif user_type == 'client':
                query = query.where(User.user_type == UserType.CLIENT)

        result = await self._session.execute(query)
        return result.scalar_one()

    # ============================================================
    # MÉTODOS DE SOFT DELETE
    # ============================================================

    async def soft_delete(self, public_id: str) -> Optional[User]:
        """Soft delete: marca o usuário como deletado"""
        user = await self.get_by_public_id(public_id)
        if user:
            user.deleted_at = datetime.now()
            user.is_active = False
            await self._session.commit()
            await self._session.refresh(user)
        return user

    async def restore(self, public_id: str) -> Optional[User]:
        """Restaura um usuário deletado"""
        user = await self.get_deleted_by_public_id(public_id)
        if user:
            user.deleted_at = None
            user.is_active = True
            await self._session.commit()
            await self._session.refresh(user)
        return user

    async def hard_delete(self, public_id: str) -> bool:
        """Remove permanentemente um usuário do banco"""
        user = await self.get_by_public_id(public_id, include_deleted=True)
        if user:
            await self._session.delete(user)
            await self._session.commit()
            return True
        return False


class UserQueryRepository(UserBaseRepository, UserQueriesMixin):
    """Repository focado em operações de consulta."""

    pass
