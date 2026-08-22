from datetime import datetime, timezone
from typing import Any, Generic, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute

from .base_mixin import BaseMixin, ModelType


class UtilityMixin(BaseMixin[ModelType], Generic[ModelType]):
    """Mixin para métodos utilitários"""

    async def soft_delete(self, public_id: str) -> Optional[ModelType]:
        if not hasattr(self._model, 'deleted_at'):
            raise AttributeError("Model has no 'deleted_at' for soft delete")
        # NOTA: update vem do CRUDMixin,
        # que estará disponível no repositório final
        return await self.update(
            public_id, deleted_at=datetime.now(timezone.utc)
        )

    async def restore(self, public_id: str) -> Optional[ModelType]:
        if not hasattr(self._model, 'deleted_at'):
            raise AttributeError("Model has no 'deleted_at' for restore")
        return await self.update(public_id, deleted_at=None)

    async def get_random(self, limit: int = 1) -> List[ModelType]:
        result = await self._session.execute(
            select(self._model).order_by(func.random()).limit(limit)
        )
        return result.scalars().all()

    async def get_latest(self, limit: int = 10) -> List[ModelType]:
        if not hasattr(self._model, 'created_at'):
            raise AttributeError("Model has no 'created_at' field")
        # NOTA: get_all vem do QueryMixin,
        # que estará disponível no repositório final
        return await self.get_all(
            order_by='created_at', descending=True, limit=limit
        )

    async def get_oldest(self, limit: int = 10) -> List[ModelType]:
        if not hasattr(self._model, 'created_at'):
            raise AttributeError("Model has no 'created_at' field")
        return await self.get_all(
            order_by='created_at', descending=False, limit=limit
        )

    async def get_by_ids(self, ids: List[int]) -> List[ModelType]:
        if not ids:
            return []
        result = await self._session.execute(
            select(self._model).where(self._model.id.in_(ids))
        )
        return result.scalars().all()

    async def get_where_in(
        self, field: InstrumentedAttribute, values: List[Any]
    ) -> List[ModelType]:
        if not values:
            return []
        result = await self._session.execute(
            select(self._model).where(field.in_(values))
        )
        return result.scalars().all()
