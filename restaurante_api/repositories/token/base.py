"""
Token Base Repository - Herda todos os mixins.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select

from restaurante_api.core.dependencies import Session
from restaurante_api.models.reset_token import PasswordResetToken
from restaurante_api.repositories.mixins import (
    BaseMixin,
    CRUDMixin,
    QueryMixin,
)
from restaurante_api.utilits.token_generator import generate_numeric_token


class TokenBaseRepository(
    CRUDMixin[PasswordResetToken],
    QueryMixin[PasswordResetToken],
):
    """
    Repositório base para tokens de reset de senha.
    Herda todos os mixins que fornecem funcionalidades diferentes.
    """

    def __init__(self, session: Session):
        # Inicializa todos os mixins com session e model
        BaseMixin.__init__(self, session, PasswordResetToken)

    # ==================== MÉTODOS DE TRANSAÇÃO ====================

    async def commit(self):
        """Faz commit da transação atual."""
        await self._session.commit()

    async def rollback(self):
        """Faz rollback da transação atual."""
        await self._session.rollback()

    async def flush(self):
        """Faz flush da sessão (não commit)."""
        await self._session.flush()

    async def refresh(self, instance):
        """Atualiza uma instância com dados do banco."""
        await self._session.refresh(instance)

    # ======= MÉTODOS ESPECÍFICOS PARA TOKENS =========

    async def get_valid_token(
        self, token: str, email: str = None
    ) -> Optional[PasswordResetToken]:
        """
        Busca um token válido (não expirado e não usado).

        Args:
            token: O token a ser buscado
            email: Email do usuário (opcional, para verificação extra)

        Returns:
            Token válido ou None
        """
        query = select(self._model).where(
            and_(
                self._model.token == token,
                self._model.used_at.is_(None),
                self._model.expires_at > datetime.now(timezone.utc),
            )
        )

        result = await self._session.execute(query)
        token_obj = result.scalar_one_or_none()

        # Se forneceu email, verifica se pertence ao usuário
        if token_obj and email:
            user = await self._session.execute(
                select(self._model.user).where(
                    self._model.user_id == token_obj.user_id
                )
            )
            user_obj = user.scalar_one_or_none()
            if user_obj and user_obj.email != email:
                return None

        return token_obj

    async def mark_as_used(self, token: PasswordResetToken) -> None:
        """Marca um token como usado."""
        token.used_at = datetime.now(timezone.utc)
        await self.commit()

    async def get_by_user_id(
        self, user_id: int
    ) -> Optional[PasswordResetToken]:
        """Busca token por ID do usuário (não usado)."""
        result = await self._session.execute(
            select(self._model).where(
                and_(
                    self._model.user_id == user_id,
                    self._model.used_at.is_(None),
                    self._model.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_all_user_tokens(self, user_id: int) -> int:
        """
        Invalida todos os tokens ativos de um usuário.
        Útil quando o usuário troca a senha.

        Returns:
            Número de tokens invalidados
        """
        result = await self._session.execute(
            select(self._model).where(
                and_(
                    self._model.user_id == user_id,
                    self._model.used_at.is_(None),
                    self._model.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        tokens = result.scalars().all()

        for token in tokens:
            token.used_at = datetime.now(timezone.utc)

        await self.commit()
        return len(tokens)

    async def delete_expired_tokens(self) -> int:
        """
        Remove tokens expirados do banco (hard delete).

        Returns:
            Número de tokens removidos
        """
        result = await self._session.execute(
            select(self._model).where(
                self._model.expires_at <= datetime.now(timezone.utc)
            )
        )
        expired_tokens = result.scalars().all()

        count = len(expired_tokens)
        for token in expired_tokens:
            await self._session.delete(token)

        await self.commit()
        return count

    async def create_token(
        self, user_id: int, expires_minutes: int = 30
    ) -> PasswordResetToken:
        """
        Cria um novo token para o usuário.

        Args:
            user_id: ID do usuário
            expires_minutes: Minutos até expirar (padrão: 30)

        Returns:
            Token criado
        """

        token = generate_numeric_token()
        date_now = datetime.now(timezone.utc)
        expires_at = date_now + timedelta(minutes=expires_minutes)

        reset_token = self._model(
            user_id=user_id, token=token, expires_at=expires_at
        )

        self._session.add(reset_token)
        await self.flush()
        await self.refresh(reset_token)

        return reset_token
