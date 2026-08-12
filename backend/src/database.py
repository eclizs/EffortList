from .models import User, Entry, Base

from sqlalchemy import Engine, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from .config import settings

engine = create_async_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# async def run():
#     await init_db()

#     async with engine.connect() as conn:
#         result = await conn.exec_driver_sql("PRAGMA foreign_keys")
#         print(result.scalar())

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(run())