# restaurante_api/schemas/produto.py

from datetime import datetime
from typing import Annotated, Optional

from fastapi import Form
from pydantic import BaseModel, Field

from restaurante_api.models.produto import CategoriaProduto


class ProduceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0, description='Preço em Kz')
    category: CategoriaProduto
    subcategory: Optional[str] = Field(None, max_length=50)
    is_available: bool = True


class ProduceCreate(ProduceBase):
    """Payload de criação."""

    @classmethod
    def as_form(  # noqa: PLR0913, PLR0917
        cls,
        name: Annotated[str, Form(min_length=1, max_length=100)],
        price: Annotated[float, Form(gt=0)],
        category: Annotated[CategoriaProduto, Form()],
        description: Annotated[Optional[str], Form(max_length=500)] = None,
        subcategory: Annotated[Optional[str], Form(max_length=50)] = None,
        is_available: Annotated[bool, Form()] = True,
    ) -> 'ProduceCreate':
        return cls(
            name=name,
            price=price,
            category=category,
            description=description,
            subcategory=subcategory,
            is_available=is_available,
        )


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
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
