from datetime import datetime, timedelta, timezone

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_as_dataclass, mapped_column

from restaurante_api.core.database import table_registry
from restaurante_api.utilits.token_generator import generate_numeric_token


@mapped_as_dataclass(table_registry)
class PasswordResetToken:
    __tablename__ = 'password_reset_tokens'

    # 1. ID - Chave primária
    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True
    )

    # 2. user_id - Chave estrangeira (relaciona com User)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )

    # 3. token - O token único (atenção ao unique=True e index=True)
    token: Mapped[str] = mapped_column(
        String(6),
        init=False,
        unique=True,
        index=True,
        nullable=False,
        default=generate_numeric_token(),
    )

    # 4. expires_at - Quando o token expira
    expires_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc) + timedelta(minutes=30),
        nullable=False,
    )

    # 5. used_at - Quando foi usado (permite NULL)
    used_at: Mapped[datetime] = mapped_column(nullable=True, default=None)

    # 6. created_at - Quando foi criado
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    # melhorar performance de queries comuns
    __table_args__ = (
        Index('ix_reset_token_user_lookup', 'user_id', 'token'),
        Index('ix_reset_token_expires', 'expires_at'),
    )
