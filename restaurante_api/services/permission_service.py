# restaurante_api/services/permission_service.py

from typing import Optional, Union

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
        user: Optional[User], resource_owner_id: Union[int, str, None]
    ) -> None:
        """
        Verifica se o usuário é o dono do recurso ou administrador.

        Args:
            user: Usuário atual
            resource_owner_id: ID do dono do recurso (pode ser int ou str)
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuário não autenticado',
            )

        # ✅ Admin tem acesso a tudo
        if user.user_type == UserType.ADMIN:
            return

        # ✅ Se não houver dono do recurso, permite (para recursos sem dono)
        if resource_owner_id is None:
            return

        # ✅ Verifica se o usuário é o dono do recurso
        is_owner = False

        # Compara por ID (int)
        if isinstance(resource_owner_id, int):
            is_owner = user.id == resource_owner_id
        # Compara por public_id (str)
        elif isinstance(resource_owner_id, str):
            is_owner = user.public_id == resource_owner_id
        else:
            # Se for outro tipo, tenta converter para string
            is_owner = str(user.public_id) == str(resource_owner_id)

        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para acessar este recurso',
            )

    @staticmethod
    def can_manage_products(user: Optional[User]) -> bool:
        """Verifica se o usuário pode gerenciar produtos"""
        return user is not None and user.user_type == UserType.ADMIN

    @staticmethod
    def is_admin(user: Optional[User]) -> bool:
        """Verifica se o usuário é administrador (sem levantar exceção)"""
        return user is not None and user.user_type == UserType.ADMIN
