#!/usr/bin/env python3
"""
AEGIS License Server - License Issuer

Issues signed JWT licenses for AEGIS-protected Odoo modules.
"""

import jwt
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class LicenseIssuer:
    """
    Issues and signs AEGIS licenses using Ed25519/JWT.
    """
    
    def __init__(self, private_key_path: str, key_id: str = "aegis-2026-01"):
        """
        Initialize the license issuer.
        
        Args:
            private_key_path: Path to Ed25519 private key (PEM format)
            key_id: Key identifier for JWT 'kid' header
        """
        self.key_id = key_id
        self.private_key = self._load_private_key(private_key_path)
        self.issuer = "https://license.biz4a.com"
    
    def _load_private_key(self, key_path: str) -> ed25519.Ed25519PrivateKey:
        """Load Ed25519 private key from PEM file."""
        key_path_obj = Path(key_path)
        if not key_path_obj.exists():
            raise FileNotFoundError(f"Private key not found: {key_path}")
        
        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None  # No password for POC
            )
        
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Key is not an Ed25519 private key")
        
        return private_key
    
    def issue_license(
        self,
        customer_id: str,
        customer_name: str,
        module_name: str,
        allowed_versions: List[str],
        license_type: str = "perpetual",
        duration_days: Optional[int] = None,
        instance_fingerprint: Optional[str] = None
    ) -> str:
        """
        Issue a signed license JWT.
        
        Args:
            customer_id: Unique customer identifier (e.g., 'CUST-001')
            customer_name: Customer display name
            module_name: Technical name of Odoo module
            allowed_versions: List of allowed Odoo major versions (e.g., ['17', '18'])
            license_type: 'perpetual', 'subscription', or 'demo'
            duration_days: License duration (required for subscription/demo)
            instance_fingerprint: Optional instance binding (sha256 hash)
        
        Returns:
            Signed JWT license string
        """
        # Validate license type
        valid_types = ["perpetual", "subscription", "demo"]
        if license_type not in valid_types:
            raise ValueError(f"Invalid license_type. Must be one of: {valid_types}")
        
        # Generate unique license ID
        license_id = str(uuid.uuid4())
        
        # Current timestamp
        now = datetime.now(timezone.utc)
        issued_at = int(now.timestamp())
        
        # Calculate expiration
        # Note: For perpetual licenses, we omit 'exp' claim entirely
        # rather than setting it to null (PyJWT doesn't handle null well)
        expires_at = None
        if license_type in ["subscription", "demo"]:
            if duration_days is None:
                raise ValueError(f"{license_type} licenses require duration_days")
            expiry_time = now + timedelta(days=duration_days)
            expires_at = int(expiry_time.timestamp())
        
        # Build JWT payload
        payload = {
            # Standard JWT claims
            "jti": license_id,           # JWT ID
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
        
        # Add expiration only if license has one (subscription/demo)
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
    
    def decode_license(self, token: str, verify: bool = False) -> Dict[str, Any]:
        """
        Decode a license JWT (for debugging/inspection).
        
        Args:
            token: JWT license string
            verify: Whether to verify signature (requires public key)
        
        Returns:
            Decoded payload dictionary
        """
        return jwt.decode(
            token,
            options={"verify_signature": verify}
        )


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


# Example usage / CLI interface
if __name__ == "__main__":
    import sys
    import json
    
    print("=" * 70)
    print("AEGIS License Issuer - POC Demo")
    print("=" * 70)
    
    # Initialize issuer
    private_key_path = "keys/aegis-2026-01.private.pem"
    
    try:
        issuer = LicenseIssuer(private_key_path, key_id="aegis-2026-01")
        print(f"✅ Loaded private key: {private_key_path}\n")
    except Exception as e:
        print(f"❌ Error loading private key: {e}")
        sys.exit(1)
    
    # Example 1: Perpetual License
    print("📜 Example 1: Perpetual License")
    print("-" * 70)
    
    perpetual_license = issuer.issue_license(
        customer_id="CUST-001",
        customer_name="Acme Corporation",
        module_name="biz4a_payroll_drc",
        allowed_versions=["17", "18"],
        license_type="perpetual"
    )
    
    print(f"License Token:\n{perpetual_license}\n")
    
    # Decode to show payload
    decoded = issuer.decode_license(perpetual_license)
    print(f"Decoded Payload:\n{json.dumps(decoded, indent=2)}\n")
    
    # Example 2: 30-Day Demo License
    print("\n📜 Example 2: 30-Day Demo License")
    print("-" * 70)
    
    demo_license = issuer.issue_license(
        customer_id="DEMO-123",
        customer_name="Prospect Inc",
        module_name="biz4a_payroll_drc",
        allowed_versions=["18"],
        license_type="demo",
        duration_days=30
    )
    
    print(f"License Token:\n{demo_license}\n")
    decoded = issuer.decode_license(demo_license)
    print(f"Decoded Payload:\n{json.dumps(decoded, indent=2)}\n")
    
    # Example 3: Instance-Bound License
    print("\n📜 Example 3: Instance-Bound Perpetual License")
    print("-" * 70)
    
    fingerprint = generate_instance_fingerprint(
        db_uuid="550e8400-e29b-41d4-a716-446655440000",
        domain="acme.odoo.com"
    )
    
    bound_license = issuer.issue_license(
        customer_id="CUST-002",
        customer_name="SecureCorp Ltd",
        module_name="biz4a_accounting_ohada",
        allowed_versions=["17"],
        license_type="perpetual",
        instance_fingerprint=fingerprint
    )
    
    print(f"Instance Fingerprint: {fingerprint}")
    print(f"License Token:\n{bound_license}\n")
    decoded = issuer.decode_license(bound_license)
    print(f"Decoded Payload:\n{json.dumps(decoded, indent=2)}\n")
    
    # Save examples to files
    output_dir = Path("licenses")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "example-perpetual.jwt", "w") as f:
        f.write(perpetual_license)
    
    with open(output_dir / "example-demo.jwt", "w") as f:
        f.write(demo_license)
    
    with open(output_dir / "example-bound.jwt", "w") as f:
        f.write(bound_license)
    
    print("=" * 70)
    print("✅ Example licenses saved to licenses/ directory")
    print("=" * 70)
