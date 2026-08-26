# restaurante_api/core/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import registry

from restaurante_api.core.settings import Settings

table_registry = registry()

engine = create_async_engine(Settings().DATABASE_URL)

# Fábrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session():
    """Dependência para obter uma sessão do banco de dados."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
