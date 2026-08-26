from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserType(str, Enum):
    CLIENT = 'client'
    ADMIN = 'admin'


class UserTypeUpdate(BaseModel):
    """Schema para atualização do tipo de usuário"""

    user_type: str


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserSchema):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone: Optional[str] = None


class UserPublic(BaseModel):
    username: str
    email: EmailStr
    phone: Optional[str] = None
    user_type: str
    public_id: str
    is_active: Optional[bool] = True
    deleted_at: Optional[datetime] = None


class UserList(BaseModel):
    users: list[UserPublic]
    total: int
    page: int
    per_page: int


class UserWithToken(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = 'bearer'


class UserFilterSchema(BaseModel):
    """Schema para filtros de usuário."""

    public_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

    # NOVOS CAMPOS
    search: Optional[str] = Field(
        None, description='Buscar por nome, email ou telefone'
    )
    user_type: Optional[str] = Field(
        None, description='Filtrar por tipo (admin/client)'
    )
    active_only: bool = Field(True, description='Apenas usuários ativos')
    include_deleted: bool = Field(
        False, description='Incluir usuários deletados'
    )
    limit: int = Field(50, ge=1, le=100, description='Limite de resultados')
    offset: int = Field(0, ge=0, description='Pular N resultados')

    class Config:
        arbitrary_types_allowed = True

    def to_filters_dict(self) -> dict:
        """Retorna apenas os campos que não são None."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
