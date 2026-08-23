# restaurante_api/models/mesa.py

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_as_dataclass,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from restaurante_api.models.reserva_mesa import ReservaMesa


from restaurante_api.core.database import table_registry


class StatusMesa(str, enum.Enum):
    """Status possíveis para uma mesa"""

    DISPONIVEL = 'disponivel'
    RESERVADA = 'reservada'
    OCUPADA = 'ocupada'
    EM_LIMPEZA = 'em_limpeza'
    INDISPONIVEL = 'indisponivel'
    CONFIRMADA = 'confirmada'


class TipoMesa(str, enum.Enum):
    """Tipos de mesa"""

    PADRAO = 'padrao'
    JANTAR = 'jantar'
    VIP = 'vip'
    EXTERNA = 'externa'
    BAR = 'bar'


@mapped_as_dataclass(table_registry)
class Mesa:
    __tablename__ = 'mesas'

    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True
    )

    # CAMPOS OBRIGATÓRIOS
    numero: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    capacidade: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StatusMesa] = mapped_column(
        Enum(StatusMesa),
        nullable=False,
        default=StatusMesa.DISPONIVEL,
    )
    tipo: Mapped[TipoMesa] = mapped_column(
        Enum(TipoMesa),
        nullable=False,
        default=TipoMesa.PADRAO,
    )

    # CAMPOS OPCIONAIS
    descricao: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )
    localizacao: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # CAMPOS DE IDENTIFICAÇÃO

    public_id: Mapped[str] = mapped_column(
        String(36),
        init=False,
        unique=True,
        index=True,
        nullable=False,
        default_factory=lambda: str(uuid.uuid4()),
    )

    # TIMESTAMPS
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # RELACIONAMENTOS
    reservas: Mapped[List['ReservaMesa']] = relationship(
        'ReservaMesa',
        back_populates='mesa',
        lazy='selectin',
        cascade='all, delete-orphan',
        init=False,
    )
