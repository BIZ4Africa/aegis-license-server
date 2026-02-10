"""
AEGIS License Server - API Schemas
Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator


# ===== Customer Schemas =====

class CustomerBase(BaseModel):
    """Base customer schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Customer name")
    email: Optional[EmailStr] = Field(None, description="Customer email")
    company: Optional[str] = Field(None, max_length=200, description="Company name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    address: Optional[str] = Field(None, description="Postal address")
    notes: Optional[str] = Field(None, description="Internal notes")


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""
    id: str = Field(..., min_length=1, max_length=50, description="Unique customer ID")
    
    @field_validator("id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer ID format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Customer ID must be alphanumeric (with optional - or _)")
        return v


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    company: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ===== License Schemas =====

class LicenseCreate(BaseModel):
    """Schema for creating a new license."""
    customer_id: str = Field(..., description="Customer ID")
    module_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Technical name of Odoo module"
    )
    allowed_major_versions: list[str] = Field(
        ...,
        min_length=1,
        description="List of allowed Odoo major versions (e.g., ['17', '18'])"
    )
    license_type: str = Field(
        ...,
        description="License type: perpetual, subscription, or demo"
    )
    duration_days: Optional[int] = Field(
        None,
        ge=1,
        description="Duration in days (required for subscription/demo)"
    )
    instance_fingerprint: Optional[str] = Field(
        None,
        description="Optional instance fingerprint for binding"
    )
    notes: Optional[str] = Field(None, description="Internal notes")
    
    @field_validator("license_type")
    @classmethod
    def validate_license_type(cls, v: str) -> str:
        """Validate license type."""
        valid = ["perpetual", "subscription", "demo"]
        if v not in valid:
            raise ValueError(f"license_type must be one of: {valid}")
        return v
    
    @field_validator("allowed_major_versions")
    @classmethod
    def validate_versions(cls, v: list[str]) -> list[str]:
        """Validate version format."""
        for version in v:
            if not version.isdigit():
                raise ValueError(f"Version must be a number, got: {version}")
        return v


class LicenseResponse(BaseModel):
    """Schema for license response."""
    id: UUID
    customer_id: str
    module_name: str
    license_type: str
    allowed_major_versions: str  # Stored as comma-separated in DB
    issued_at: datetime
    expires_at: Optional[datetime]
    status: str
    revoked_at: Optional[datetime]
    revoked_reason: Optional[str]
    instance_fingerprint: Optional[str]
    token: str
    key_id: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    customer: Optional[CustomerResponse] = None
    
    model_config = {"from_attributes": True}


class LicenseListResponse(BaseModel):
    """Schema for paginated license list."""
    licenses: list[LicenseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ===== License Validation Schemas =====

class LicenseValidationRequest(BaseModel):
    """Schema for license validation request."""
    token: str = Field(..., description="JWT license token")
    module_name: str = Field(..., description="Module being validated")
    odoo_version: str = Field(..., description="Odoo major version (e.g., '17')")
    instance_db_uuid: Optional[str] = Field(None, description="Database UUID")
    instance_domain: Optional[str] = Field(None, description="Instance domain")


class LicenseValidationResponse(BaseModel):
    """Schema for license validation response."""
    valid: bool = Field(..., description="Whether license is valid")
    license_id: Optional[str] = Field(None, description="License UUID")
    license_type: Optional[str] = Field(None, description="License type")
    customer_name: Optional[str] = Field(None, description="Customer name")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    error: Optional[str] = Field(None, description="Error message if invalid")


# ===== License Revocation Schema =====

class LicenseRevoke(BaseModel):
    """Schema for revoking a license."""
    reason: str = Field(..., min_length=1, description="Reason for revocation")


# ===== Fingerprint Schema =====

class FingerprintRequest(BaseModel):
    """Schema for generating instance fingerprint."""
    db_uuid: str = Field(..., description="Odoo database UUID")
    domain: str = Field(..., description="Instance domain name")


class FingerprintResponse(BaseModel):
    """Schema for fingerprint response."""
    fingerprint: str = Field(..., description="Generated SHA-256 fingerprint")
    db_uuid: str
    domain: str


# ===== Health & Info Schemas =====

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment")
    database: str = Field(..., description="Database status")


class InfoResponse(BaseModel):
    """Schema for server info response."""
    app_name: str
    version: str
    environment: str
    issuer: str
    key_id: str


# ===== Error Schemas =====

class ErrorDetail(BaseModel):
    """Schema for error details."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[list[ErrorDetail]] = Field(None, description="Additional error details")
