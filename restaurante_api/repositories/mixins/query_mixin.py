from typing import Any, Generic, List, Optional, Tuple, Union

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from .base_mixin import BaseMixin, ModelType


class QueryMixin(BaseMixin[ModelType], Generic[ModelType]):
    """Mixin para operações de busca e consulta"""

    # NOTA: get_by_filters, filter_by,
    # search NÃO dependem de CRUDMixin
    # Eles são independentes e usam apenas select()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Union[str, InstrumentedAttribute]] = None,
        descending: bool = False,
    ) -> List[ModelType]:
        query = select(self._model)
        if order_by:
            if isinstance(order_by, str):
                order_by = getattr(self._model, order_by, None)
                if order_by is None:
                    raise AttributeError(
                        f"Model has no attribute '{order_by}'"
                    )
            if descending:
                query = query.order_by(order_by.desc())
            else:
                query = query.order_by(order_by)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_by_filters(self, **filters) -> Optional[ModelType]:
        query = select(self._model)
        for key, value in filters.items():
            if hasattr(self._model, key):
                query = query.where(getattr(self._model, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def filter_by(self, **filters) -> List[ModelType]:
        query = select(self._model)
        for key, value in filters.items():
            if hasattr(self._model, key):
                query = query.where(getattr(self._model, key) == value)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def find_by(
        self, conditions: List[Tuple[InstrumentedAttribute, str, Any]]
    ) -> List[ModelType]:
        if not conditions:
            return await self.get_all()
        query = select(self._model)
        filters = []
        for field, operator, value in conditions:
            if operator == '==':
                filters.append(field == value)
            elif operator == '!=':
                filters.append(field != value)
            elif operator == '>':
                filters.append(field > value)
            elif operator == '>=':
                filters.append(field >= value)
            elif operator == '<':
                filters.append(field < value)
            elif operator == '<=':
                filters.append(field <= value)
            elif operator == 'like':
                filters.append(field.like(value))
            elif operator == 'ilike':
                filters.append(field.ilike(value))
            elif operator == 'in':
                filters.append(field.in_(value))
            else:
                raise ValueError(f'Operador não suportado: {operator}')
        query = query.where(and_(*filters))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def search(
        self, search_term: str, fields: List[str], case_sensitive: bool = False
    ) -> List[ModelType]:
        if not fields:
            raise ValueError('At least one field must be provided')
        query = select(self._model)
        conditions = []
        for field_name in fields:
            if hasattr(self._model, field_name):
                field = getattr(self._model, field_name)
                if case_sensitive:
                    conditions.append(field.like(f'%{search_term}%'))
                else:
                    conditions.append(field.ilike(f'%{search_term}%'))
        if conditions:
            query = query.where(or_(*conditions))
        result = await self._session.execute(query)
        return result.scalars().all()
