# repositories/mixins/aggregate_mixin.py
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute

from .base_mixin import BaseMixin, ModelType


class AggregateMixin(BaseMixin[ModelType]):
    """Mixin para operações de agregação e contagem"""

    async def count(self, **filters) -> int:
        """Conta o número de registros que correspondem
        aos filtros fornecidos.
        Exemplo de uso:
        await user_repo.count(active=True)
        para contar usuários ativos.
        """
        query = select(func.count()).select_from(self._model)
        for key, value in filters.items():
            if hasattr(self._model, key):
                query = query.where(getattr(self._model, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def exists(self, **filters) -> bool:
        """Verifica se existe
        pelo menos um registro que corresponde
        aos filtros fornecidos."""
        count = await self.count(**filters)
        return count > 0

    async def aggregate_sum(self, field: InstrumentedAttribute) -> float:
        result = await self._session.execute(
            select(func.sum(field)).select_from(self._model)
        )
        return result.scalar_one() or 0.0

    async def aggregate_avg(self, field: InstrumentedAttribute) -> float:
        result = await self._session.execute(
            select(func.avg(field)).select_from(self._model)
        )
        return result.scalar_one() or 0.0

    async def aggregate_min(self, field: InstrumentedAttribute) -> Any:
        result = await self._session.execute(
            select(func.min(field)).select_from(self._model)
        )
        return result.scalar_one()

    async def aggregate_max(self, field: InstrumentedAttribute) -> Any:
        result = await self._session.execute(
            select(func.max(field)).select_from(self._model)
        )
        return result.scalar_one()
