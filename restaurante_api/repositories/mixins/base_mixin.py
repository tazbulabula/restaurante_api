# repositories/mixins/base_mixin.py
from typing import Generic, Type, TypeVar

from sqlalchemy import String, cast, or_, select

from restaurante_api.core.dependencies import Session

ModelType = TypeVar('ModelType')


class BaseMixin(Generic[ModelType]):
    """Classe base que fornece os atributos necessários"""

    def __init__(self, session: Session, model: Type[ModelType]):
        self._session = session
        self._model = model

    @property
    def session(self):
        return self._session

    def search_query(
        self,
        search_term: str,
        fields: list[str],
        case_sensitive: bool = False,
    ):
        """
        Constrói uma query que procura `search_term` em qualquer dos `fields`.

        Args:
            search_term: termo a procurar (ILIKE %termo%)
            fields: lista de nomes de atributos do modelo
                    (ex: ['username', 'email', 'phone'])
            case_sensitive: se True, usa LIKE (case-sensitive);
                            se False, usa ILIKE (case-insensitive)

        Returns:
            Select — query pronta para `.where(...)` adicional
        """
        query = select(self._model)

        if not search_term:
            return query

        termo = f'%{search_term}%'
        condicoes = []

        for field in fields:
            coluna = getattr(self._model, field, None)
            if coluna is None:
                continue

            # cast para String garante que campos não-string
            # (ex: phone se for Integer) também funcionam
            col = cast(coluna, String)
            if case_sensitive:
                condicoes.append(col.like(termo))
            else:
                condicoes.append(col.ilike(termo))

        if condicoes:
            query = query.where(or_(*condicoes))

        return query
