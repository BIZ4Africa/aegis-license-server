"""
AEGIS License Server - License Service
Core business logic for license issuance and verification.
Reuses cryptographic logic from POC.
"""

import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .config import settings


class LicenseService:
    """
    Service for creating and signing license JWTs.
    
    This class encapsulates the cryptographic operations for license management.
    """
    
    def __init__(self, private_key_path: Optional[Path] = None, key_id: Optional[str] = None):
        """
        Initialize the license service.
        
        Args:
            private_key_path: Path to Ed25519 private key (defaults to settings)
            key_id: Key identifier for JWT 'kid' header (defaults to settings)
        """
        self.private_key_path = private_key_path or settings.private_key_path
        self.key_id = key_id or settings.key_id
        self.issuer = settings.license_issuer
        
        # Load private key on initialization
        self.private_key = self._load_private_key()
    
    def _load_private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load Ed25519 private key from PEM file."""
        if not self.private_key_path.exists():
            raise FileNotFoundError(
                f"Private key not found: {self.private_key_path}\n"
                f"Generate keys using: python scripts/generate_keys.py"
            )
        
        with open(self.private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None  # TODO: Support encrypted keys in production
            )
        
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError(
                f"Key at {self.private_key_path} is not an Ed25519 private key"
            )
        
        return private_key
    
    def issue_license(
        self,
        license_id: UUID,
        customer_id: str,
        customer_name: str,
        module_name: str,
        allowed_versions: list[str],
        license_type: str,
        duration_days: Optional[int] = None,
        instance_fingerprint: Optional[str] = None,
    ) -> str:
        """
        Issue a signed license JWT.
        
        Args:
            license_id: Unique license UUID
            customer_id: Customer identifier
            customer_name: Customer display name
            module_name: Technical name of Odoo module
            allowed_versions: List of allowed Odoo major versions
            license_type: 'perpetual', 'subscription', or 'demo'
            duration_days: License duration (required for subscription/demo)
            instance_fingerprint: Optional instance binding (sha256 hash)
        
        Returns:
            Signed JWT license string
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate license type
        valid_types = ["perpetual", "subscription", "demo"]
        if license_type not in valid_types:
            raise ValueError(f"Invalid license_type. Must be one of: {valid_types}")
        
        # Current timestamp
        now = datetime.now(timezone.utc)
        issued_at = int(now.timestamp())
        
        # Calculate expiration
        expires_at = None
        if license_type in ["subscription", "demo"]:
            if duration_days is None:
                raise ValueError(f"{license_type} licenses require duration_days")
            expiry_time = now + timedelta(days=duration_days)
            expires_at = int(expiry_time.timestamp())
        
        # Build JWT payload
        payload = {
            # Standard JWT claims
            "jti": str(license_id),      # JWT ID
            "iss": self.issuer,           # Issuer
            "iat": issued_at,             # Issued At
            
            # AEGIS-specific claims
            "customer": {
                "id": customer_id,
                "name": customer_name
            },
            "module": {
                "technical_name": module_name,
                "allowed_major_versions": allowed_versions
            },
            "license_type": license_type,
        }
        
        # Add expiration if present
        if expires_at is not None:
            payload["exp"] = expires_at
        
        # Add optional instance fingerprint
        if instance_fingerprint:
            payload["instance_fingerprint"] = instance_fingerprint
        
        # Sign JWT with Ed25519
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm="EdDSA",
            headers={"kid": self.key_id}
        )
        
        return token
    
    def verify_license(self, token: str, public_key_path: Optional[Path] = None) -> dict:
        """
        Verify a license JWT signature.
        
        This is mainly for server-side verification/debugging.
        Clients will have their own embedded public keys.
        
        Args:
            token: JWT license string
            public_key_path: Path to public key (defaults to settings)
        
        Returns:
            Decoded and validated payload
        
        Raises:
            jwt.InvalidTokenError: If verification fails
        """
        public_key_path = public_key_path or settings.public_key_path
        
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        # Verify signature and decode
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["EdDSA"],
            options={
                "verify_signature": True,
                "verify_exp": False,  # We handle expiration in business logic
                "require": ["jti", "iss", "iat"]
            }
        )
        
        # Verify issuer
        if payload.get("iss") != self.issuer:
            raise jwt.InvalidIssuerError(
                f"Invalid issuer: expected '{self.issuer}', got '{payload.get('iss')}'"
            )
        
        return payload
    
    @staticmethod
    def generate_instance_fingerprint(db_uuid: str, domain: str) -> str:
        """
        Generate an instance fingerprint for license binding.
        
        Args:
            db_uuid: Odoo database UUID
            domain: Instance domain name
        
        Returns:
            SHA-256 fingerprint string (e.g., 'sha256:abc123...')
        """
        combined = f"{db_uuid}:{domain}".encode('utf-8')
        hash_obj = hashlib.sha256(combined)
        return f"sha256:{hash_obj.hexdigest()}"


# Global service instance (initialized on first import)
_license_service: Optional[LicenseService] = None


def get_license_service() -> LicenseService:
    """
    Get the global LicenseService instance.
    
    This is a singleton to avoid reloading keys on every request.
    """
    global _license_service
    if _license_service is None:
        _license_service = LicenseService()
    return _license_service
