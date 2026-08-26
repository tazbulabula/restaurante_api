# restaurante_api/models/pedido.py

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
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

if TYPE_CHECKING:
    from restaurante_api.models.item_pedido import ItemPedido
    from restaurante_api.models.reserva_mesa import ReservaMesa
    from restaurante_api.models.user import User


class StatusPedido(str, enum.Enum):
    """Status do pedido"""

    AGUARDANDO_PAGAMENTO = 'aguardando_pagamento'
    AGUARDANDO_CONFIRMACAO_MANUAL = 'aguardando_confirmacao_manual'
    PAGO = 'pago'
    PREPARANDO = 'preparando'
    PRONTO = 'pronto'
    ENTREGUE = 'entregue'
    CANCELADO = 'cancelado'


class TipoCliente(str, enum.Enum):
    """Tipo de cliente que fez o pedido"""

    REGISTRADO = 'registrado'
    CONVIDADO = 'convidado'


class OrigemPedido(str, enum.Enum):
    """Onde o pedido foi feito"""

    PRESENCIAL = 'presencial'
    DELIVERY = 'delivery'
    RESERVA = 'reserva'


class MetodoPagamento(str, enum.Enum):
    """Métodos de pagamento disponíveis"""

    EMIS = 'emis'
    DINHEIRO = 'dinheiro'
    TRANSFERENCIA = 'transferencia'
    POS = 'pos'
    BOLETO = 'boleto'


@mapped_as_dataclass(table_registry)
class Pedido:
    __tablename__ = 'pedidos'

    # ============================================================
    # 1. CAMPOS OBRIGATÓRIOS (SEM VALOR PADRÃO)
    # ============================================================
    mesa_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    cliente_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cliente_telefone: Mapped[str] = mapped_column(String(20), nullable=False)

    # ============================================================
    # 2. CAMPOS COM VALOR PADRÃO (OPCIONAIS NO CONSTRUTOR)
    # ============================================================
    cliente_tipo: Mapped[TipoCliente] = mapped_column(
        Enum(TipoCliente),
        nullable=False,
        default=TipoCliente.CONVIDADO,
    )
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[StatusPedido] = mapped_column(
        Enum(StatusPedido),
        nullable=False,
        default=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    origem: Mapped[OrigemPedido] = mapped_column(
        Enum(OrigemPedido),
        nullable=False,
        default=OrigemPedido.PRESENCIAL,
    )
    observacoes: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )
    tempo_preparo_estimado: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )

    # ============================================================
    # 3. CAMPOS DE PAGAMENTO (COM DEFAULT)
    # ============================================================
    pagamento_manual: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    metodo_pagamento: Mapped[Optional[MetodoPagamento]] = mapped_column(
        Enum(MetodoPagamento),
        nullable=True,
        default=None,
    )
    pagamento_autorizado_por: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None,  # <--- ADICIONADO default=None
    )

    # ============================================================
    # 4. DADOS DE PAGAMENTO (OPCIONAIS)
    # ============================================================
    transacao_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default=None
    )
    pagamento_dados: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None
    )
    pagamento_confirmado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )
    codigo_autorizacao: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None
    )

    # ============================================================
    # 5. CHAVES ESTRANGEIRAS (OPCIONAIS)
    # ============================================================
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('users.id'), nullable=True, default=None
    )
    reserva_mesa_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('reservas_mesa.id'),
        nullable=True,
        index=True,
        default=None,
    )

    # ============================================================
    # 6. CAMPOS DE IDENTIFICAÇÃO (init=False)
    # ============================================================
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

    # ============================================================
    # 7. TIMESTAMPS (init=False)
    # ============================================================
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # ============================================================
    # 8. RELACIONAMENTOS (init=False)
    # ============================================================
    usuario: Mapped[Optional['User']] = relationship(
        'User',
        back_populates='pedidos',
        lazy='selectin',
        init=False,
    )
    itens: Mapped[List['ItemPedido']] = relationship(
        'ItemPedido',
        back_populates='pedido',
        cascade='all, delete-orphan',
        lazy='selectin',
        init=False,
    )
    reserva_mesa: Mapped[Optional['ReservaMesa']] = relationship(
        'ReservaMesa',
        back_populates='pedido',
        lazy='selectin',
        foreign_keys=[reserva_mesa_id],
        init=False,
    )
