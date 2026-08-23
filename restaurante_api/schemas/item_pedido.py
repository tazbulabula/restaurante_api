# restaurante_api/schemas/test_pedido.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ============ ITEM PEDIDO ============


class ItemPedidoBase(BaseModel):
    produto_id: int = Field(..., description='ID do produto')
    quantidade: int = Field(..., ge=1, description='Quantidade do produto')
    observacoes: Optional[str] = Field(
        None, max_length=200, description='Observações do item'
    )


class ItemPedidoCreate(ItemPedidoBase):
    pass


class ItemPedidoUpdate(BaseModel):
    quantidade: Optional[int] = Field(None, ge=1)
    observacoes: Optional[str] = Field(None, max_length=200)


class ItemPedidoResponse(ItemPedidoBase):
    id: int
    public_id: str
    pedido_id: int
    preco_unitario: float
    subtotal: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemPedidoDetalhadoResponse(ItemPedidoResponse):
    produto_nome: Optional[str] = None
    produto_categoria: Optional[str] = None
