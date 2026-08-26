"""User Repository -
Fachada unificada que combina todos os repositórios especializados."""

from restaurante_api.core.dependencies import Session
from restaurante_api.models.user import User, UserType

from .base import UserBaseRepository
from .queries import UserQueriesMixin, UserQueryRepository
from .relations import UserRelationRepository, UserRelationsMixin
from .stats import UserStatsMixin, UserStatsRepository
from .updates import UserUpdateRepository, UserUpdatesMixin
from .validations import UserValidationRepository, UserValidationsMixin


class UserRepository(
    UserBaseRepository,
    UserQueriesMixin,
    UserUpdatesMixin,
    UserValidationsMixin,
    UserRelationsMixin,
    UserStatsMixin,
):
    """
    Repositório unificado para usuários.

    Combina todos os mixins especializados,
    mas o Ruff conta apenas os métodos
    públicos explícitos desta classe (que são poucos),
    não os métodos herdados.
    """

    def __init__(self, session: Session):
        super().__init__(session)

    # Métodos adicionais

    async def delete_by_email(self, email: str) -> bool:
        """Deleta usuário por email (hard delete)."""
        user = await self.get_by_email(email)
        if user:
            return await self.delete(user.public_id)
        return False


# Opcional: Exportar também repositórios especializados se necessário
__all__ = [
    'UserRepository',
    'UserBaseRepository',
    'UserQueryRepository',
    'UserUpdateRepository',
    'UserValidationRepository',
    'UserRelationRepository',
    'UserStatsRepository',
    'UserType',
    'User',
]
