"""
AEGIS License Server - Licenses Router
Core license management endpoints.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import License, Customer, LicenseStatus, AuditLog
from ..schemas import (
    LicenseCreate,
    LicenseResponse,
    LicenseListResponse,
    LicenseValidationRequest,
    LicenseValidationResponse,
    LicenseRevoke,
    FingerprintRequest,
    FingerprintResponse,
)
from ..services import get_license_service
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def issue_license(
    license_data: LicenseCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a new signed license.
    
    This creates a license record and generates a signed JWT token.
    The token can be deployed to the customer's Odoo instance.
    """
    # Verify customer exists
    result = await db.execute(
        select(Customer).where(Customer.id == license_data.customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{license_data.customer_id}' not found. Create customer first.",
        )
    
    # Validate duration for subscription/demo licenses
    if license_data.license_type in ["subscription", "demo"]:
        if not license_data.duration_days:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{license_data.license_type} licenses require duration_days",
            )
    
    # Generate license ID
    license_id = uuid4()
    
    # Get license service and issue JWT
    license_service = get_license_service()
    
    try:
        token = license_service.issue_license(
            license_id=license_id,
            customer_id=customer.id,
            customer_name=customer.name,
            module_name=license_data.module_name,
            allowed_versions=license_data.allowed_major_versions,
            license_type=license_data.license_type,
            duration_days=license_data.duration_days,
            instance_fingerprint=license_data.instance_fingerprint,
        )
    except Exception as e:
        logger.error("Failed to issue license", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign license: {str(e)}",
        )
    
    # Calculate expiration date
    expires_at = None
    if license_data.duration_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=license_data.duration_days)
    
    # Create license record
    db_license = License(
        id=license_id,
        customer_id=customer.id,
        module_name=license_data.module_name,
        license_type=license_data.license_type,
        allowed_major_versions=",".join(license_data.allowed_major_versions),
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        status=LicenseStatus.ACTIVE,
        instance_fingerprint=license_data.instance_fingerprint,
        token=token,
        key_id=license_service.key_id,
        notes=license_data.notes,
    )
    
    db.add(db_license)
    
    # Create audit log
    audit_log = AuditLog(
        license_id=license_id,
        event_type="issued",
        customer_id=customer.id,
        module_name=license_data.module_name,
        event_data=f"License issued: {license_data.license_type}",
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(db_license)
    
    logger.info(
        "License issued",
        license_id=str(license_id),
        customer_id=customer.id,
        module=license_data.module_name,
        type=license_data.license_type,
    )
    
    return db_license


@router.get("/licenses/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a license by ID."""
    from uuid import UUID
    
    try:
        license_uuid = UUID(license_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid license ID format (must be UUID)",
        )
    
    result = await db.execute(
        select(License)
        .where(License.id == license_uuid)
        .options(selectinload(License.customer))
    )
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License '{license_id}' not found",
        )
    
    return license_obj


@router.get("/licenses", response_model=LicenseListResponse)
async def list_licenses(
    customer_id: str = Query(None, description="Filter by customer ID"),
    module_name: str = Query(None, description="Filter by module name"),
    license_type: str = Query(None, description="Filter by license type"),
    status_filter: str = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List licenses with filtering and pagination.
    """
    # Build query
    query = select(License).options(selectinload(License.customer))
    
    if customer_id:
        query = query.where(License.customer_id == customer_id)
    
    if module_name:
        query = query.where(License.module_name == module_name)
    
    if license_type:
        query = query.where(License.license_type == license_type)
    
    if status_filter:
        query = query.where(License.status == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    licenses = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return LicenseListResponse(
        licenses=licenses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/licenses/validate", response_model=LicenseValidationResponse)
async def validate_license(
    validation: LicenseValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a license token.
    
    This endpoint can be called by Odoo instances to validate their license.
    It checks:
    - Signature validity
    - Expiration
    - Module match
    - Version compatibility
    - Instance binding (if present)
    """
    license_service = get_license_service()
    
    try:
        # Verify JWT signature
        payload = license_service.verify_license(validation.token)
        
        license_id = payload.get("jti")
        license_type = payload.get("license_type")
        customer_name = payload.get("customer", {}).get("name")
        module = payload.get("module", {})
        
        # Check module name
        if module.get("technical_name") != validation.module_name:
            return LicenseValidationResponse(
                valid=False,
                error=f"License is for module '{module.get('technical_name')}', not '{validation.module_name}'",
            )
        
        # Check Odoo version
        allowed_versions = module.get("allowed_major_versions", [])
        if validation.odoo_version not in allowed_versions:
            return LicenseValidationResponse(
                valid=False,
                error=f"Odoo version '{validation.odoo_version}' not allowed. Allowed: {allowed_versions}",
            )
        
        # Check expiration
        exp = payload.get("exp")
        if exp:
            from datetime import datetime, timezone
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            if datetime.now(timezone.utc) >= exp_dt:
                return LicenseValidationResponse(
                    valid=False,
                    license_id=license_id,
                    license_type=license_type,
                    error="License has expired",
                    expires_at=exp_dt,
                )
        
        # Check instance binding if required
        instance_fp = payload.get("instance_fingerprint")
        if instance_fp:
            if not validation.instance_db_uuid or not validation.instance_domain:
                return LicenseValidationResponse(
                    valid=False,
                    error="License is bound to an instance, but instance details not provided",
                )
            
            computed_fp = license_service.generate_instance_fingerprint(
                validation.instance_db_uuid,
                validation.instance_domain,
            )
            
            if instance_fp != computed_fp:
                return LicenseValidationResponse(
                    valid=False,
                    error="Instance fingerprint mismatch. License is bound to a different instance.",
                )
        
        # Check if license is revoked in database
        from uuid import UUID
        result = await db.execute(
            select(License).where(License.id == UUID(license_id))
        )
        db_license = result.scalar_one_or_none()
        
        if db_license and db_license.status == LicenseStatus.REVOKED:
            return LicenseValidationResponse(
                valid=False,
                license_id=license_id,
                error="License has been revoked",
            )
        
        # All checks passed
        return LicenseValidationResponse(
            valid=True,
            license_id=license_id,
            license_type=license_type,
            customer_name=customer_name,
            expires_at=exp_dt if exp else None,
        )
    
    except Exception as e:
        logger.error("License validation failed", error=str(e))
        return LicenseValidationResponse(
            valid=False,
            error=f"Validation error: {str(e)}",
        )


@router.delete("/licenses/{license_id}/revoke")
async def revoke_license(
    license_id: str,
    revoke_data: LicenseRevoke,
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a license.
    
    Revoked licenses will fail validation checks.
    """
    from uuid import UUID
    
    try:
        license_uuid = UUID(license_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid license ID format",
        )
    
    result = await db.execute(
        select(License).where(License.id == license_uuid)
    )
    license_obj = result.scalar_one_or_none()
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License '{license_id}' not found",
        )
    
    if license_obj.status == LicenseStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="License is already revoked",
        )
    
    # Revoke license
    license_obj.status = LicenseStatus.REVOKED
    license_obj.revoked_at = datetime.now(timezone.utc)
    license_obj.revoked_reason = revoke_data.reason
    
    # Create audit log
    audit_log = AuditLog(
        license_id=license_uuid,
        event_type="revoked",
        customer_id=license_obj.customer_id,
        module_name=license_obj.module_name,
        event_data=f"Revoked: {revoke_data.reason}",
    )
    db.add(audit_log)
    
    await db.commit()
    
    logger.info(
        "License revoked",
        license_id=str(license_id),
        reason=revoke_data.reason,
    )
    
    return {"message": "License revoked successfully", "license_id": str(license_id)}


@router.post("/licenses/fingerprint", response_model=FingerprintResponse)
async def generate_fingerprint(fingerprint_data: FingerprintRequest):
    """
    Generate an instance fingerprint.
    
    This utility endpoint helps generate fingerprints for instance-bound licenses.
    """
    license_service = get_license_service()
    
    fingerprint = license_service.generate_instance_fingerprint(
        fingerprint_data.db_uuid,
        fingerprint_data.domain,
    )
    
    return FingerprintResponse(
        fingerprint=fingerprint,
        db_uuid=fingerprint_data.db_uuid,
        domain=fingerprint_data.domain,
    )
