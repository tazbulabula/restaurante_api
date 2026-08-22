# tests/factories/user_factory.py
import factory
from faker import Faker as FakeGenerator

from restaurante_api.core.security import hash_password
from restaurante_api.schemas.user import UserCreate, UserType

fake = FakeGenerator()

# Garantir que o Faker gere números angolanos
FAKE_ANGOLA_PREFIXES = ['91', '92', '93', '94', '95', '96', '97', '98', '99']


def generate_angola_phone() -> str:
    """Gera um número de telefone angolano válido para testes.

    Exemplos:
        +244 91X XXX XXX
        +244 92X XXX XXX
        +244 99X XXX XXX
    """
    prefix = fake.random_element(elements=FAKE_ANGOLA_PREFIXES)
    # Primeiro dígito após prefixo (0-9)
    third_digit = fake.random_int(min=0, max=9)
    # Restante do número (6 dígitos)
    rest = fake.random_number(digits=6, fix_len=True)

    return f'+244 {prefix}{third_digit} {str(rest)[:3]} {str(rest)[3:]}'


class UserFactory(factory.Factory):
    """Factory para criação de usuários em testes."""

    class Meta:
        model = UserCreate

    username = factory.Sequence(lambda n: f'testuser_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@exemplo.com')
    password = factory.LazyAttribute(lambda _: 'Test@123')
    phone = factory.LazyAttribute(lambda _: generate_angola_phone())
    user_type = UserType.CLIENT

    @classmethod
    async def create_in_repo(cls, repo, commit: bool = True, **override):
        """Cria E PERSISTE usando o repositório."""
        # Cria o objeto UserCreate
        user_create = cls.build(**override)

        # Converte para dicionário para modificar a senha
        data = user_create.model_dump()  # ← Converte para dict

        # Hash da senha antes de salvar
        data['password'] = hash_password(data['password'])

        # Cria no repositório (que espera **kwargs)
        user = await repo.create(**data)

        if commit:
            await repo.commit()

        return user

    @classmethod
    async def create_batch_in_repo(
        cls, repo, size: int, commit_each: bool = False, **override
    ):
        """
        Cria lote de usuários em uma única chamada.

        Exemplo:
            users = await UserFactory.create_batch_in_repo(user_repo, 50)
        """
        users = []
        for i in range(size):
            # Garante usernames únicos no lote
            override_copy = override.copy()
            if 'username' not in override_copy:
                prefix = override.get('prefix', 'batch')
                override_copy['username'] = f'{prefix}_{i}'
            if 'email' not in override_copy:
                d = f'{override_copy["username"]}@example.com'
                override_copy['email'] = d

            user = await cls.create_in_repo(
                repo, commit=commit_each, **override_copy
            )
            users.append(user)

        if not commit_each:
            await repo.commit()

        return users
