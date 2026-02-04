"""
AEGIS License Server - Main Application
FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import structlog

from .config import settings
from .database import init_db, dispose_db
from .routers import licenses, customers, health, admin


# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json" 
        else structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting AEGIS License Server",
        version=settings.app_version,
        environment=settings.environment,
    )
    
    # Initialize database (only in development)
    # In production, use Alembic migrations
    if settings.is_development:
        logger.info("Initializing database (development mode)")
        await init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down AEGIS License Server")
    await dispose_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
AEGIS License Control Framework - License Server API

This API allows authorized systems to:
- Issue signed JWT licenses for Odoo modules
- Manage customers and their licenses
- Validate and revoke licenses
- Track license usage via audit logs

**Authentication:** API Key required for all endpoints (except /health)

**Security:** All licenses are cryptographically signed with Ed25519
    """,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)


# ===== Middleware =====

# CORS
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Bind request ID to structlog context
    with structlog.contextvars.bind_contextvars(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    
    response = await call_next(request)
    
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    
    return response


# ===== Exception Handlers =====

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
    )
    
    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "type": exc.__class__.__name__,
            },
        )


# ===== Include Routers =====

app.include_router(health.router, tags=["Health"])
app.include_router(licenses.router, prefix="/api/v1", tags=["Licenses"])
app.include_router(customers.router, prefix="/api/v1", tags=["Customers"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


# ===== Custom OpenAPI Schema =====

def custom_openapi():
    """Customize OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication",
        }
    }
    
    # Apply security globally (except health endpoint)
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "tags" in operation:
                if "Health" not in operation["tags"]:
                    operation["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ===== Root Endpoint =====

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "AEGIS License Server",
        "version": settings.app_version,
        "docs": "/docs" if not settings.is_production else None,
    }
