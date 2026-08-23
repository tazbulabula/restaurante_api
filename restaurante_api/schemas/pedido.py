# restaurante_api/schemas/test_pedido.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from restaurante_api.models.pedido import (
    OrigemPedido,
    StatusPedido,
    TipoCliente,
)
from restaurante_api.schemas.item_pedido import (
    ItemPedidoCreate,
    ItemPedidoDetalhadoResponse,
    ItemPedidoResponse,
)

# ============ PEDIDO ============


class PedidoBase(BaseModel):
    mesa_numero: int = Field(..., ge=1, description='Número da mesa')
    cliente_nome: str = Field(
        ..., min_length=1, max_length=100, description='Nome do cliente'
    )
    cliente_telefone: str = Field(
        ..., min_length=9, max_length=20, description='Telefone do cliente'
    )
    cliente_tipo: TipoCliente = Field(default=TipoCliente.CONVIDADO)
    observacoes: Optional[str] = Field(None, max_length=500)
    origem: OrigemPedido = Field(default=OrigemPedido.PRESENCIAL)


class PedidoCreate(PedidoBase):
    itens: List[ItemPedidoCreate] = Field(
        ..., min_length=1, description='Itens do pedido'
    )
    usuario_id: Optional[int] = Field(
        None, description='ID do usuário (se registrado)'
    )
    reserva_mesa_id: Optional[int] = Field(
        None, description='ID da reserva de mesa'
    )


class PedidoUpdate(BaseModel):
    mesa_numero: Optional[int] = Field(None, ge=1)
    cliente_nome: Optional[str] = Field(None, min_length=1, max_length=100)
    cliente_telefone: Optional[str] = Field(None, min_length=9, max_length=20)
    cliente_tipo: Optional[TipoCliente] = None
    observacoes: Optional[str] = Field(None, max_length=500)
    status: Optional[StatusPedido] = None
    origem: Optional[OrigemPedido] = None
    tempo_preparo_estimado: Optional[int] = Field(None, ge=1)


class PedidoStatusUpdate(BaseModel):
    status: StatusPedido = Field(..., description='Novo status do pedido')


class PedidoResponse(PedidoBase):
    id: int
    public_id: str
    total: float
    status: StatusPedido
    origem: OrigemPedido
    usuario_id: Optional[int]
    reserva_mesa_id: Optional[int]
    transacao_id: Optional[str]
    pagamento_confirmado_em: Optional[datetime]
    codigo_autorizacao: Optional[str]
    tempo_preparo_estimado: Optional[int]
    created_at: datetime
    updated_at: datetime
    itens: List[ItemPedidoResponse] = []

    class Config:
        from_attributes = True


class PedidoDetalhadoResponse(PedidoResponse):
    usuario_nome: Optional[str] = None
    itens_detalhados: List[ItemPedidoDetalhadoResponse] = []


class PedidoFiltros(BaseModel):
    """Filtros para listagem de pedidos"""

    status: Optional[StatusPedido] = Field(
        None, description='Filtrar por status'
    )
    origem: Optional[OrigemPedido] = Field(
        None, description='Filtrar por origem'
    )
    data_inicio: Optional[datetime] = Field(None, description='Data inicial')
    data_fim: Optional[datetime] = Field(None, description='Data final')
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PedidoPagamentoResponse(BaseModel):
    pedido_id: int
    pedido_public_id: str
    total: float
    transacao_id: Optional[str] = None
    status: StatusPedido
    mensagem: str
