# restaurante_api/models/produto.py

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_as_dataclass, mapped_column

from restaurante_api.core.database import table_registry


class CategoriaProduto(str, enum.Enum):
    """Categorias de produtos do restaurante"""

    # Comidas
    ENTRADA = 'entrada'
    PRINCIPAL = 'principal'
    GUARNICAO = 'guarnicao'
    SOBREMESA = 'sobremesa'

    # Bebidas
    BEBIDA = 'bebida'
    REFRIGERANTE = 'refrigerante'
    SUCOS = 'sucos'
    CERVEJA = 'cerveja'
    VINHO = 'vinho'
    CAFE = 'cafe'

    # Outros
    PETISCO = 'petisco'
    PORCOES = 'porcoes'
    DOCES = 'doces'
    SALGADOS = 'salgados'
    VEGETARIANO = 'vegetariano'
    VEGANO = 'vegano'


@mapped_as_dataclass(table_registry)
class Produto:
    __tablename__ = 'produtos'

    # 1. CAMPOS OBRIGATÓRIOS (sem valor padrão) - TODOS JUNTOS
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[CategoriaProduto] = mapped_column(
        Enum(CategoriaProduto),
        nullable=False,
        default=CategoriaProduto.PRINCIPAL,
    )

    # 2. CAMPOS OPCIONAIS (com valor padrão) - TODOS DEPOIS
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )
    subcategory: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )

    # 3. CAMPOS DE IDENTIFICAÇÃO (init=False) - NÃO AFETAM A ORDEM
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

    # 4. TIMESTAMPS (init=False)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )
