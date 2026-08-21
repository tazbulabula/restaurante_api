from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import registry

from restaurante_api.core.settings import Settings

table_registry = registry()

engine = create_async_engine(Settings().DATABASE_URL)


async def get_session():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
