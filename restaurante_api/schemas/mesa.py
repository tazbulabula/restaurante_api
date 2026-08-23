# restaurante_api/schemas/mesa.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from restaurante_api.models.mesa import StatusMesa, TipoMesa

# ============ MESA ============


class MesaBase(BaseModel):
    numero: int = Field(..., ge=1, description='Número da mesa')
    capacidade: int = Field(
        ..., ge=1, description='Capacidade máxima de pessoas'
    )
    tipo: TipoMesa = Field(default=TipoMesa.PADRAO)
    descricao: Optional[str] = Field(None, max_length=200)
    localizacao: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class MesaFiltros(BaseModel):
    """Filtros para listagem de mesas"""

    status_mesa: Optional[StatusMesa] = Field(
        None, description='Filtrar por status'
    )
    tipo: Optional[TipoMesa] = Field(None, description='Filtrar por tipo')
    disponivel: Optional[bool] = Field(
        None, description='Filtrar por disponibilidade (is_active)'
    )
    limit: int = Field(50, ge=1, le=100, description='Limite de resultados')
    offset: int = Field(0, ge=0, description='Pular N resultados')


class MesaCreate(MesaBase):
    status: StatusMesa = Field(default=StatusMesa.DISPONIVEL)


class MesaUpdate(BaseModel):
    numero: Optional[int] = Field(None, ge=1)
    capacidade: Optional[int] = Field(None, ge=1)
    status: Optional[StatusMesa] = None
    tipo: Optional[TipoMesa] = None
    descricao: Optional[str] = Field(None, max_length=200)
    localizacao: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class MesaResponse(MesaBase):
    id: int
    public_id: str
    status: StatusMesa
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ DISPONIBILIDADE ============


class VerificarDisponibilidadeRequest(BaseModel):
    data_hora: datetime
    numero_pessoas: int = Field(..., ge=1)
    duracao_minutos: int = Field(
        60, ge=15, le=240, description='Duração estimada em minutos'
    )


class MesaDisponivelResponse(BaseModel):
    id: int
    public_id: str
    numero: int
    capacidade: int
    tipo: TipoMesa
    localizacao: Optional[str]
    status: StatusMesa

    class Config:
        from_attributes = True


class VerificarDisponibilidadeResponse(BaseModel):
    disponivel: bool
    mesas_disponiveis: List[MesaDisponivelResponse]
