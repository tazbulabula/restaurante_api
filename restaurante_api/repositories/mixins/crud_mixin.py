from typing import Any, Dict, Generic, Optional

from pydantic import BaseModel
from sqlalchemy import delete, select, update

from .base_mixin import BaseMixin, ModelType


class CRUDMixin(BaseMixin[ModelType], Generic[ModelType]):
    """Mixin para operações CRUD básicas"""

    async def create(self, **kwargs) -> ModelType:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def create_from_dict(self, data: Dict[str, Any]) -> ModelType:
        return await self.create(**data)

    async def create_from_schema(self, schema: BaseModel) -> ModelType:
        return await self.create(**schema.model_dump())

    async def get(self, user_id: int) -> Optional[ModelType]:
        result = await self._session.execute(
            select(self._model).where(self._model.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_public_id(self, public_id: str) -> Optional[ModelType]:
        if hasattr(self._model, 'public_id'):
            result = await self._session.execute(
                select(self._model).where(self._model.public_id == public_id)
            )
            return result.scalar_one_or_none()
        raise AttributeError("Model has no attribute 'public_id'")

    async def update(self, public_id: str, **kwargs) -> Optional[ModelType]:
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if not filtered_kwargs:
            return await self.get_by_public_id(public_id)

        await self._session.execute(
            update(self._model)
            .where(self._model.public_id == public_id)
            .values(**filtered_kwargs)
        )
        await self._session.flush()
        return await self.get_by_public_id(public_id)

    async def delete(self, public_id: str) -> bool:
        result = await self._session.execute(
            delete(self._model).where(self._model.public_id == public_id)
        )
        await self._session.flush()
        return result.rowcount > 0
