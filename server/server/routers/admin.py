"""
AEGIS License Server - Admin Router
Administrative endpoints for monitoring and maintenance.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import License, Customer, AuditLog, LicenseStatus

router = APIRouter()


@router.get("/stats")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get server statistics.
    
    Returns counts of customers, licenses, and other metrics.
    """
    # Count customers
    result = await db.execute(select(func.count()).select_from(Customer))
    total_customers = result.scalar()
    
    result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.is_active == True)
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
