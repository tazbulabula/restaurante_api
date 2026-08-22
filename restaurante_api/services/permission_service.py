# restaurante_api/services/permission_service.py

from typing import Optional

from fastapi import HTTPException, status

from restaurante_api.models.user import User, UserType


class PermissionService:
    """Serviço para gerenciar permissões"""

    @staticmethod
    def require_admin(user: Optional[User]) -> None:
        """Verifica se o usuário é administrador"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuário não autenticado',
            )

        if user.user_type != UserType.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Apenas administradores podem realizar esta ação',
            )

    @staticmethod
    def require_authenticated(user: Optional[User]) -> None:
        """Verifica se o usuário está autenticado"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuário não autenticado',
            )

    @staticmethod
    def require_owner_or_admin(
        user: Optional[User], resource_owner_id: int
    ) -> None:
        """Verifica se o usuário é o dono do recurso ou administrador"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuário não autenticado',
            )

        if user.user_type == UserType.ADMIN:
            return

        if user.id != resource_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para acessar este recurso',
            )

    @staticmethod
    def can_manage_products(user: Optional[User]) -> bool:
        """Verifica se o usuário pode gerenciar produtos"""
        return user and user.user_type == UserType.ADMIN
