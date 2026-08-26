from restaurante_api.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from restaurante_api.repositories.token import TokenRepository
from restaurante_api.repositories.user import UserRepository
from restaurante_api.services.email_service import EmailService


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
        token_repo: TokenRepository,
    ):
        self.user_repo = user_repo
        self.email_service = email_service
        self.token_repo = token_repo

    async def login(self, data):
        user = await self.user_repo.get_by_email(data.username)

        if not user:
            raise ValueError('Incorrect Email.')

        if not verify_password(
            plain_password=data.password, hashed_password=user.password
        ):
            raise ValueError('Incorrect Password.')

        await self.user_repo.commit()

        new_token = create_access_token(
            data={'sub': user.public_id, 'user_type': user.user_type}
        )

        return {'access_token': new_token, 'token_type': 'bearer'}

    async def change_new_password(
        self,
        current_password: str,
        data_password: str,
        public_id: str,
    ):
        if not verify_password(
            data_password.current_password, current_password
        ):
            raise ValueError('Current password is incorrect')

        await self.user_repo.update_password(
            public_id=public_id,
            hashed_password=hash_password(data_password.new_password),
        )

        await self.user_repo.commit()

        return {'message': 'Password is been changed'}

    async def request_password_reset(self, email: str):
        """Solicita reset de senha - APENAS lógica de negócio."""

        user = await self.user_repo.get_by_email(email=email)

        if not user:
            raise ValueError('Email is incorrect.')

        # Cria token
        new_token = await self.token_repo.create(user_id=user.id)

        # Envia email
        await self.email_service.send_reset_password_email(
            to_email=email, token=new_token.token, name=user.username
        )

        # NÃO chama commit aqui - quem chama o service gerencia a transação
        return new_token.token

    async def reset_password(self, token: str, new_password: str):
        """
        Reseta a senha usando apenas o token.
        O token já tem a relação user_id.
        """
        # Busca token válido
        valid_token = await self.token_repo.get_valid_token(token)

        if not valid_token:
            raise ValueError('Invalid or expired token')

        # Busca o usuário pelo ID do token
        user = await self.user_repo.get(valid_token.user_id)

        if not user:
            raise ValueError('User not found')

        # Atualiza senha
        hashed = hash_password(new_password)
        await self.user_repo.update_password(user.public_id, hashed)

        # Marca token como usado
        await self.token_repo.mark_as_used(valid_token)

        # Opcional: invalidar todos os outros tokens do usuário
        await self.token_repo.invalidate_all_user_tokens(user.id)

        await self.user_repo.commit()
