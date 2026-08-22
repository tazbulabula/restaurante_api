from typing import Any, Dict, Generic, List, Tuple

from sqlalchemy import delete

from .base_mixin import BaseMixin, ModelType


class BulkMixin(BaseMixin[ModelType], Generic[ModelType]):
    """Mixin para operações em lote"""

    async def bulk_create(
        self, items: List[Dict[str, Any]]
    ) -> List[ModelType]:
        instances = [self._model(**item) for item in items]
        self._session.add_all(instances)
        await self._session.flush()
        for instance in instances:
            await self._session.refresh(instance)
        return instances

    async def bulk_update(
        self, updates: List[Tuple[str, Dict[str, Any]]]
    ) -> List[ModelType]:
        updated_instances = []
        for public_id, data in updates:
            # NOTA: update vem do CRUDMixin,
            # que estará disponível no repositório final
            instance = await self.update(public_id, **data)
            if instance:
                updated_instances.append(instance)
        return updated_instances

    async def delete_all(self) -> int:
        result = await self._session.execute(delete(self._model))
        await self._session.flush()
        return result.rowcount

    async def chunked_create(
        self, items: List[Dict[str, Any]], chunk_size: int = 100
    ) -> List[ModelType]:
        all_instances = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            instances = await self.bulk_create(chunk)
            all_instances.extend(instances)
            await self._session.flush()
        return all_instances

    async def chunked_update(
        self, updates: List[Tuple[str, Dict[str, Any]]], chunk_size: int = 100
    ) -> List[ModelType]:
        all_updated = []
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i : i + chunk_size]
            updated = await self.bulk_update(chunk)
            all_updated.extend(updated)
            await self._session.flush()
        return all_updated
