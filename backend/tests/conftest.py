"""
Test Configuration and Fixtures
================================
Shared fixtures for all tests
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.config import settings
from app.models.database import Base, get_db


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden dependencies"""
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers() -> dict:
    """Headers with API key for authenticated requests"""
    return {
        "X-API-Key": settings.api_secret_key,
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_message() -> str:
    """Sample user message for testing"""
    return "What is Kaso?"


@pytest.fixture
def sample_arabic_message() -> str:
    """Sample Arabic message for testing"""
    return "ما هي شركة Kaso؟"
