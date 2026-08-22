"""User Repository -
Fachada unificada que combina todos os repositórios especializados."""

from restaurante_api.core.dependencies import Session

from .base import TokenBaseRepository


class TokenRepository(TokenBaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    pass
