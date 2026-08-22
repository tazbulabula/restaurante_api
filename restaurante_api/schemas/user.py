from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserType(str, Enum):
    CLIENT = 'client'
    ADMIN = 'admin'


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

    class Config:
        # Permite usar o schema como kwargs
        arbitrary_types_allowed = True

    def to_filters_dict(self) -> dict:
        """Retorna apenas os campos que não são None."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
