# Em um service

from restaurante_api.core.security import hash_password
from restaurante_api.repositories.user import UserRepository
from restaurante_api.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_create: UserCreate):
        # Verifica se email já existe
        if await self.user_repo.email_exists(user_create.email):
            raise ValueError('Email already in use by another user')

        # Verifica se username já existe
        if await self.user_repo.username_exists(user_create.username):
            raise ValueError('Username already exists')

        # Cria usuário
        return await self.user_repo.create(
            email=user_create.email,
            username=user_create.username,
            password=hash_password(user_create.password),
            phone=user_create.phone,
        )

    async def updated_user(self, public_id, data: UserUpdate):

        # Converte para dict, excluindo campos None
        update_user = data.model_dump(exclude_unset=True)

        # Se a senha foi dornecida, separa dos demais dados
        password = update_user['password'] if update_user['password'] else None
        del update_user['password']

        """Atualiza dados do próprio usuário sem a password (perfil)."""

        # Verifica se email já existe (se estiver mudando)
        if update_user['email']:
            existing = await self.user_repo.get_by_email(update_user['email'])
            if existing and existing.public_id != public_id:
                raise ValueError('Email already in use by another user')

        if not update_user:
            # Nada para atualizar
            return await self.user_repo.get_by_public_id(public_id)

        # Atualiza a password se existir
        if password:
            await self.user_repo.update_password(
                public_id=public_id, hashed_password=password
            )

        return await self.user_repo.update(public_id, **update_user)

    async def desactive_user(self, public_id):
        return await self.user_repo.soft_delete(public_id=public_id)

    async def delete_user(self, public_id):
        return await self.user_repo.delete(public_id=public_id)
