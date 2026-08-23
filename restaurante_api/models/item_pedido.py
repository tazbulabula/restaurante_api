# restaurante_api/models/test_pedido.py

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
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
    from restaurante_api.models.pedido import Pedido
    from restaurante_api.models.produto import Produto


@mapped_as_dataclass(table_registry)
class ItemPedido:
    __tablename__ = 'itens_pedido'

    # CAMPOS OBRIGATÓRIOS
    pedido_id: Mapped[int] = mapped_column(
        ForeignKey('pedidos.id'), nullable=False
    )
    produto_id: Mapped[int] = mapped_column(
        ForeignKey('produtos.id'), nullable=False
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    # CAMPOS OPCIONAIS
    observacoes: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )

    # CAMPOS DE IDENTIFICAÇÃO
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

    # TIMESTAMPS
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # RELACIONAMENTOS
    pedido: Mapped['Pedido'] = relationship(
        'Pedido',
        back_populates='itens',
        lazy='selectin',
        init=False,
    )
    produto: Mapped['Produto'] = relationship(
        'Produto',
        lazy='selectin',
        init=False,
    )
