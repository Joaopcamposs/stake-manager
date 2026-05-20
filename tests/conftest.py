from collections.abc import AsyncGenerator

import pytest
from db import Base, get_db
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    # SQLite doesn't support schemas, remove it for tests
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(eng, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    # Restore schema
    Base.metadata.schema = "stake_manager"
    for table in Base.metadata.tables.values():
        table.schema = "stake_manager"

    await eng.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        from auth import serializer

        cookie_value = serializer.dumps({"authenticated": True})
        ac.cookies.set("session", cookie_value)
        yield ac
    app.dependency_overrides.clear()
