# restaurante_api/schemas/mesa.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from restaurante_api.models.mesa import StatusMesa
from restaurante_api.schemas.mesa import MesaDisponivelResponse, MesaResponse

# ============ RESERVA DE MESA ============


class ReservaMesaBase(BaseModel):
    mesa_id: int
    data_hora: datetime
    numero_pessoas: int = Field(..., ge=1)
    observacoes: Optional[str] = Field(None, max_length=300)


class ReservaFiltros(BaseModel):
    """Filtros para listagem de mesas"""

    status_reserva: Optional[StatusMesa] = Field(
        None, description='Filtrar por status'
    )
    data_inicio: Optional[datetime] = Field(None, description='Data inicial')
    data_fim: Optional[datetime] = Field(None, description='Data final')
    limit: Optional[int] = Field(50, ge=1, le=100)
    offset: Optional[int] = Field(0, ge=0)


class ReservaMesaCreate(ReservaMesaBase):
    cliente_nome: str = Field(..., min_length=1, max_length=100)
    cliente_telefone: str = Field(..., min_length=9, max_length=20)
    usuario_id: Optional[int] = None


class ReservaMesaUpdate(BaseModel):
    data_hora: Optional[datetime] = None
    numero_pessoas: Optional[int] = Field(None, ge=1)
    status: Optional[StatusMesa] = None
    observacoes: Optional[str] = Field(None, max_length=300)
    expira_em: Optional[datetime] = None


class ReservaMesaResponse(ReservaMesaBase):
    id: int
    public_id: str
    mesa_id: int
    usuario_id: Optional[int] = None
    cliente_nome: str
    cliente_telefone: str
    status: StatusMesa
    expira_em: Optional[datetime] = None
    pedido_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReservaMesaDetalhadaResponse(ReservaMesaResponse):
    mesa: Optional[MesaResponse] = None
    usuario_nome: Optional[str] = None


class VerificarDisponibilidadeRequest(BaseModel):
    data_hora: datetime
    numero_pessoas: int = Field(..., ge=1)
    duracao_minutos: int = Field(
        60, ge=15, description='Duração estimada da reserva em minutos'
    )


class VerificarDisponibilidadeResponse(BaseModel):
    disponivel: bool
    mesas_disponiveis: List[MesaDisponivelResponse]
    sugestoes: Optional[List[MesaDisponivelResponse]]


class ReservaMesaCancelarResponse(BaseModel):
    message: str
    reserva_id: int
    status: StatusMesa
