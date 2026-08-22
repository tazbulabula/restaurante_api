"""
User Base Repository - Herda todos os mixins.
"""

from restaurante_api.core.dependencies import Session
from restaurante_api.models.user import User
from restaurante_api.repositories.mixins import (
    AggregateMixin,
    BaseMixin,
    BulkMixin,
    CRUDMixin,
    QueryMixin,
    UtilityMixin,
)


class UserBaseRepository(
    CRUDMixin[User],
    BulkMixin[User],
    QueryMixin[User],
    AggregateMixin[User],
    UtilityMixin[User],
):
    """
    Repositório base para usuários.
    Herda todos os mixins que fornecem funcionalidades diferentes.
    """

    def __init__(self, session: Session):
        # Inicializa todos os mixins com session e model
        BaseMixin.__init__(self, session, User)

    """ CRUDMixin.__init__(self, session, User)
        BulkMixin.__init__(self, session, User)
        QueryMixin.__init__(self, session, User)
        AggregateMixin.__init__(self, session, User)
        UtilityMixin.__init__(self, session, User)"""

    # ==================== MÉTODOS DE TRANSAÇÃO ====================

    async def commit(self):
        """Faz commit da transação atual."""
        await self._session.commit()

    async def rollback(self):
        """Faz rollback da transação atual."""
        await self._session.rollback()

    async def flush(self):
        """Faz flush da sessão (não commit)."""
        await self._session.flush()

    async def refresh(self, instance):
        """Atualiza uma instância com dados do banco."""
        await self._session.refresh(instance)
