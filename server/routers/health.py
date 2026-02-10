"""
AEGIS License Server - Health Router
Health check and system info endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..schemas import HealthResponse, InfoResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns service status and database connectivity.
    No authentication required.
    """
    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
    )


@router.get("/info", response_model=InfoResponse)
async def server_info():
    """
    Get server information.
    
    Returns basic server configuration (non-sensitive).
    """
    return InfoResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        issuer=settings.license_issuer,
        key_id=settings.key_id,
    )
