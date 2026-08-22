# restaurante_api/schemas/produto.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from restaurante_api.models.produto import CategoriaProduto


class ProduceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0, description='Preço em Kz')
    category: CategoriaProduto
    subcategory: Optional[str] = Field(None, max_length=50)
    is_available: bool = True
    image_url: Optional[str] = Field(None, max_length=200)


class ProduceCreate(ProduceBase):
    pass


class ProduceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[CategoriaProduto] = None
    subcategory: Optional[str] = Field(None, max_length=50)
    is_available: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=200)


class ProduceResponse(ProduceBase):
    id: int
    public_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
