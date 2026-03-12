"""
AEGIS License Server - Admin Router
Administrative endpoints for monitoring and maintenance, plus API key management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import (
    generate_plain_api_key,
    hash_api_key,
    verify_admin_key,
    verify_api_key,
)
from ..models import APIKey, AuditLog, Customer, License, LicenseStatus
from ..schemas import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse

router = APIRouter()


@router.get("/stats")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(verify_api_key),
):
    """
    Get server statistics.

    Returns counts of customers, licenses, and other metrics.
    """
    # Count customers
    result = await db.execute(select(func.count()).select_from(Customer))
    total_customers = result.scalar()

    result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.is_active.is_(True))
    )
    active_customers = result.scalar()

    # Count licenses
    result = await db.execute(select(func.count()).select_from(License))
    total_licenses = result.scalar()

    result = await db.execute(
        select(func.count()).select_from(License).where(License.status == LicenseStatus.ACTIVE)
    )
    active_licenses = result.scalar()

    result = await db.execute(
        select(func.count()).select_from(License).where(License.status == LicenseStatus.REVOKED)
    )
    revoked_licenses = result.scalar()

    # Count by license type
    perpetual_result = await db.execute(
        select(func.count()).select_from(License).where(License.license_type == "perpetual")
    )
    perpetual_licenses = perpetual_result.scalar()

    subscription_result = await db.execute(
        select(func.count()).select_from(License).where(License.license_type == "subscription")
    )
    subscription_licenses = subscription_result.scalar()

    demo_result = await db.execute(
        select(func.count()).select_from(License).where(License.license_type == "demo")
    )
    demo_licenses = demo_result.scalar()

    # Recent audit logs count
    result = await db.execute(select(func.count()).select_from(AuditLog))
    total_audit_logs = result.scalar()

    return {
        "customers": {
            "total": total_customers,
            "active": active_customers,
            "inactive": total_customers - active_customers,
        },
        "licenses": {
            "total": total_licenses,
            "active": active_licenses,
            "revoked": revoked_licenses,
            "by_type": {
                "perpetual": perpetual_licenses,
                "subscription": subscription_licenses,
                "demo": demo_licenses,
            },
        },
        "audit_logs": {
            "total": total_audit_logs,
        },
    }


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(verify_api_key),
):
    """
    Get recent audit logs.

    Returns the most recent license-related events.
    """
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "license_id": str(log.license_id) if log.license_id else None,
            "customer_id": log.customer_id,
            "module_name": log.module_name,
            "event_data": log.event_data,
            "created_at": log.created_at,
        }
        for log in logs
    ]


# ===== API Key Management Endpoints =====


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description=(
        "Creates a new API key. The plain key is returned **once** — store it securely. "
        "Requires the admin secret key (api_secret_key from server configuration) "
        "in the X-API-Key header to bootstrap access."
    ),
)
async def create_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """
    Create a new API key.

    The plain key is returned only once. Store it securely.
    Authentication uses the server's api_secret_key (from configuration).
    """
    plain_key = generate_plain_api_key()
    key_hash = hash_api_key(plain_key)

    db_api_key = APIKey(
        key_hash=key_hash,
        name=key_data.name,
        description=key_data.description,
        can_issue_licenses=key_data.can_issue_licenses,
        can_revoke_licenses=key_data.can_revoke_licenses,
        can_view_customers=key_data.can_view_customers,
        expires_at=key_data.expires_at,
        created_by=key_data.created_by,
        created_at=datetime.now(timezone.utc),
    )

    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    return APIKeyCreateResponse(
        id=db_api_key.id,
        name=db_api_key.name,
        description=db_api_key.description,
        can_issue_licenses=db_api_key.can_issue_licenses,
        can_revoke_licenses=db_api_key.can_revoke_licenses,
        can_view_customers=db_api_key.can_view_customers,
        is_active=db_api_key.is_active,
        last_used_at=db_api_key.last_used_at,
        usage_count=db_api_key.usage_count,
        expires_at=db_api_key.expires_at,
        created_at=db_api_key.created_at,
        created_by=db_api_key.created_by,
        key=plain_key,
    )


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
    summary="List all API keys",
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """
    List all API keys (without the plain key values).

    Authentication uses the server's api_secret_key (from configuration).
    """
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = result.scalars().all()
    return keys


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """
    Revoke (deactivate) an API key by ID.

    The key is deactivated, not deleted, so usage history is preserved.
    Authentication uses the server's api_secret_key (from configuration).
    """
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID {key_id} not found",
        )

    api_key.is_active = False
    await db.commit()

    return None

