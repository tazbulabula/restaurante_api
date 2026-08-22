import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_as_dataclass, mapped_column

from restaurante_api import table_registry
from restaurante_api.schemas.user import UserType


@mapped_as_dataclass(table_registry)
class User:
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True
    )
    public_id: Mapped[str] = mapped_column(
        String(36),
        init=False,
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]
    phone: Mapped[Optional[str]] = mapped_column(nullable=True)
    user_type: Mapped[UserType] = mapped_column(
        nullable=False, default=UserType.CLIENT
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        init=False,
        nullable=True,
        default=None,
        index=True,
    )
