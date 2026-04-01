"""Test configuration — SQLite for local testing."""

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_clarifi.db"
os.environ["GOOGLE_API_KEY"] = "test-key"

from clarifi.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///./test_clarifi.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # Clean up test db file
    if os.path.exists("./test_clarifi.db"):
        os.unlink("./test_clarifi.db")


@pytest_asyncio.fixture
async def session(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
