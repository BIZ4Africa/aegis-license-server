"""
AEGIS License Server - Database Models
SQLAlchemy 2.0 ORM models for licenses, customers, and audit logs.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Boolean, Text, Enum as SQLEnum, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class LicenseType(str, enum.Enum):
    """License type enumeration."""
    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    DEMO = "demo"


class LicenseStatus(str, enum.Enum):
    """License status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


# ===== Models =====

class Customer(Base):
    """
    Customer entity.
    
    Represents a BIZ4A customer who can have one or more licenses.
    """
    __tablename__ = "customers"
    
    # Primary Key
    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    licenses: Mapped[list["License"]] = relationship(
        "License", 
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name})>"


class License(Base):
    """
    License entity.
    
    Stores issued licenses with their signed JWT tokens.
    """
    __tablename__ = "licenses"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    customer_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # License Details
    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    license_type: Mapped[LicenseType] = mapped_column(
        SQLEnum(LicenseType, name="license_type_enum"),
        nullable=False,
        index=True
    )
    
    # Versions
    allowed_major_versions: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Comma-separated list of allowed Odoo major versions (e.g., '17,18')"
    )
    
    # Dates
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # Status
    status: Mapped[LicenseStatus] = mapped_column(
        SQLEnum(LicenseStatus, name="license_status_enum"),
        default=LicenseStatus.ACTIVE,
        nullable=False,
        index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Instance Binding (optional)
    instance_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        index=True,
        comment="SHA-256 fingerprint for instance binding"
    )
    
    # JWT Token
    token: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Signed JWT license token"
    )
    
    # Key Information
    key_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Key ID used to sign this license (for key rotation)"
    )
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="licenses")
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="license",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<License(id={self.id}, module={self.module_name}, type={self.license_type})>"
    
    @property
    def is_active(self) -> bool:
        """Check if license is currently active."""
        if self.status != LicenseStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
    
    @property
    def allowed_versions_list(self) -> list[str]:
        """Get allowed versions as a list."""
        return [v.strip() for v in self.allowed_major_versions.split(",")]


class AuditLog(Base):
    """
    Audit log for license operations.
    
    Tracks all license-related events for security and compliance.
    """
    __tablename__ = "audit_logs"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    license_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Event Details
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Event type: issued, validated, revoked, etc."
    )
    event_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded event details"
    )
    
    # Context
    customer_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    module_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Request Information
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    license: Mapped[Optional["License"]] = relationship("License", back_populates="audit_logs")
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event={self.event_type}, license_id={self.license_id})>"


class APIKey(Base):
    """
    API Key for server-to-server authentication.
    
    Used by BIZ4A internal systems to issue licenses.
    """
    __tablename__ = "api_keys"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Key Details
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Bcrypt hash of the API key"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Friendly name for this API key"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Permissions
    can_issue_licenses: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_revoke_licenses: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view_customers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Usage Tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name})>"
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is currently valid."""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
