# restaurante_api/models/reserva_mesa.py

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
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

from restaurante_api.core.database import table_registry
from restaurante_api.models.mesa import StatusMesa

if TYPE_CHECKING:
    from restaurante_api.models.mesa import Mesa
    from restaurante_api.models.pedido import Pedido
    from restaurante_api.models.user import User


@mapped_as_dataclass(table_registry)
class ReservaMesa:
    """Registro de reservas de mesa (histórico)"""

    __tablename__ = 'reservas_mesa'

    # CAMPOS OBRIGATÓRIOS
    mesa_id: Mapped[int] = mapped_column(
        ForeignKey('mesas.id'), nullable=False
    )
    cliente_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cliente_telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    data_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    numero_pessoas: Mapped[int] = mapped_column(Integer, nullable=False)

    # CAMPOS OPCIONAIS (COM DEFAULT)
    status: Mapped[StatusMesa] = mapped_column(
        Enum(StatusMesa),
        nullable=False,
        default=StatusMesa.RESERVADA,
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('users.id'),
        nullable=True,
        default=None,
    )

    observacoes: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, default=None
    )
    expira_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )

    # CAMPOS DE IDENTIFICAÇÃO (init=False)
    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True
    )
    public_id: Mapped[str] = mapped_column(
        String(36),
        init=False,
        unique=True,
        index=True,
        nullable=False,
        default_factory=lambda: str(uuid.uuid4()),
    )

    # TIMESTAMPS (init=False)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # RELACIONAMENTOS (init=False)
    mesa: Mapped['Mesa'] = relationship(
        'Mesa',
        back_populates='reservas',
        init=False,
    )
    usuario: Mapped[Optional['User']] = relationship(
        'User',
        back_populates='reservas',
        lazy='selectin',
        init=False,
    )
    pedido: Mapped[Optional['Pedido']] = relationship(
        'Pedido',
        lazy='selectin',
        init=False,
    )
