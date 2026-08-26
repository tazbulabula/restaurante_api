# repositories/mixins/base_mixin.py
from typing import Generic, Type, TypeVar

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
