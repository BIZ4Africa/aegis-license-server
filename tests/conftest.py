"""
AEGIS License Server - Test Configuration
Shared fixtures for all tests.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Patch SQLite to handle PostgreSQL UUID type (for test compatibility)
from sqlalchemy.dialects.sqlite import base as sqlite_base
if not hasattr(sqlite_base.SQLiteTypeCompiler, "visit_UUID"):
    sqlite_base.SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(32)"

from server.database import get_db
from server.dependencies import hash_api_key, generate_plain_api_key
from server.main import app
from server.models import Base, APIKey


# Use SQLite in-memory database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _ensure_test_keys() -> None:
    """Generate Ed25519 test keys if they don't exist."""
    from pathlib import Path
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )
    from server.config import settings

    private_path = settings.private_key_path
    public_path = settings.public_key_path

    if not private_path.exists() or not public_path.exists():
        private_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        private_path.write_bytes(
            private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        )
        public_path.write_bytes(
            private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        )


# Ensure keys exist before any test runs
_ensure_test_keys()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create an in-memory SQLite engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine):
    """Provide a test database session."""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine):
    """Provide an async test client with the test database."""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def plain_api_key() -> str:
    """Generate a plain API key for use in tests."""
    return generate_plain_api_key()


@pytest_asyncio.fixture(scope="function")
async def api_key_with_all_permissions(test_db: AsyncSession, plain_api_key: str) -> tuple[APIKey, str]:
    """
    Create an API key with all permissions and return (db_object, plain_key).
    """
    db_api_key = APIKey(
        key_hash=hash_api_key(plain_api_key),
        name="Test Full Key",
        can_issue_licenses=True,
        can_revoke_licenses=True,
        can_view_customers=True,
        is_active=True,
    )
    test_db.add(db_api_key)
    await test_db.commit()
    await test_db.refresh(db_api_key)
    return db_api_key, plain_api_key


@pytest_asyncio.fixture(scope="function")
async def api_key_issue_only(test_db: AsyncSession) -> tuple[APIKey, str]:
    """Create an API key with only issue_licenses permission."""
    plain_key = generate_plain_api_key()
    db_api_key = APIKey(
        key_hash=hash_api_key(plain_key),
        name="Test Issue-Only Key",
        can_issue_licenses=True,
        can_revoke_licenses=False,
        can_view_customers=True,
        is_active=True,
    )
    test_db.add(db_api_key)
    await test_db.commit()
    await test_db.refresh(db_api_key)
    return db_api_key, plain_key
