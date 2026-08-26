# restaurante_api/models/password_reset_token.py

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurante_api.core.database import table_registry

if TYPE_CHECKING:
    from restaurante_api.models.user import User


@table_registry.mapped_as_dataclass
class PasswordResetToken:
    __tablename__ = 'password_reset_tokens'

    # Campos
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Identificação
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

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    user: Mapped['User'] = relationship(
        'User',
        lazy='selectin',
        init=False,
    )
