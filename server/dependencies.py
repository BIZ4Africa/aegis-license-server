"""
AEGIS License Server - FastAPI Dependencies
API key authentication and permission checking dependencies.
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import APIKey
import structlog

logger = structlog.get_logger()

# Password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_api_key(plain_key: str) -> str:
    """Hash an API key using bcrypt."""
    return pwd_context.hash(plain_key)


def verify_api_key_hash(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against a bcrypt hash."""
    return pwd_context.verify(plain_key, hashed_key)


def generate_plain_api_key() -> str:
    """Generate a cryptographically secure random API key."""
    return f"aegis_{secrets.token_urlsafe(32)}"


async def verify_api_key(
    x_api_key: str = Header(..., description="API Key for authentication"),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Verify the X-API-Key header against database-stored API keys.

    Returns the matching APIKey object if valid.
    Raises HTTP 401 if the key is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )

    # Fetch all active keys and verify using bcrypt
    # For a license server with a small number of keys, this is acceptable.
    result = await db.execute(
        select(APIKey).where(APIKey.is_active.is_(True))
    )
    active_keys = result.scalars().all()

    matching_key: Optional[APIKey] = None
    for api_key in active_keys:
        try:
            if verify_api_key_hash(x_api_key, api_key.key_hash):
                matching_key = api_key
                break
        except Exception:
            # Ignore malformed hashes
            continue

    if not matching_key:
        logger.warning("Invalid API key attempt")
        raise credentials_exception

    if not matching_key.is_valid:
        logger.warning("Expired or inactive API key used", key_id=matching_key.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Update usage tracking
    matching_key.last_used_at = datetime.now(timezone.utc)
    matching_key.usage_count += 1
    await db.commit()

    logger.info("API key authenticated", key_id=matching_key.id, key_name=matching_key.name)
    return matching_key


async def require_can_issue_licenses(
    api_key: APIKey = Depends(verify_api_key),
) -> APIKey:
    """Require the API key to have can_issue_licenses permission."""
    if not api_key.can_issue_licenses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to issue licenses",
        )
    return api_key


async def require_can_revoke_licenses(
    api_key: APIKey = Depends(verify_api_key),
) -> APIKey:
    """Require the API key to have can_revoke_licenses permission."""
    if not api_key.can_revoke_licenses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to revoke licenses",
        )
    return api_key


async def require_can_view_customers(
    api_key: APIKey = Depends(verify_api_key),
) -> APIKey:
    """Require the API key to have can_view_customers permission."""
    if not api_key.can_view_customers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to view customers",
        )
    return api_key


async def verify_admin_key(
    x_api_key: str = Header(..., description="Admin API Key (api_secret_key from config)"),
) -> str:
    """
    Verify access to admin API key management endpoints.

    Accepts the api_secret_key from configuration, which serves as the
    bootstrap admin token for creating the first API key.
    """
    if not secrets.compare_digest(x_api_key, settings.api_secret_key):
        logger.warning("Invalid admin key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
