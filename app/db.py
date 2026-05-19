from collections.abc import AsyncGenerator

from config import settings
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_url = settings.database_url
for _old in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
    if _url.startswith(_old):
        _url = "postgresql+psycopg://" + _url[len(_old) :]
        break

engine = create_async_engine(_url, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

metadata = MetaData(schema="bet_tracker")


class Base(DeclarativeBase):
    metadata = metadata


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
