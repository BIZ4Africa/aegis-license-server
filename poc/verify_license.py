#!/usr/bin/env python3
"""
AEGIS Odoo Client - License Verifier (POC Simulation)

Simulates the license verification logic that would run in an Odoo module.
This would be embedded in the AEGIS client module in production.
"""

import jwt
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class LicenseVerificationError(Exception):
    """Raised when license verification fails."""
    pass


class LicenseVerifier:
    """
    Verifies AEGIS license signatures and business rules.
    
    This class simulates what would be embedded in an Odoo module.
    """
    
    def __init__(self, public_key_path: str, expected_issuer: str = "https://license.biz4a.com"):
        """
        Initialize the license verifier.
        
        Args:
            public_key_path: Path to Ed25519 public key (PEM format)
            expected_issuer: Expected JWT issuer claim
        """
        self.public_key = self._load_public_key(public_key_path)
        self.expected_issuer = expected_issuer
    
    def _load_public_key(self, key_path: str) -> ed25519.Ed25519PublicKey:
        """Load Ed25519 public key from PEM file."""
        key_path_obj = Path(key_path)
        if not key_path_obj.exists():
            raise FileNotFoundError(f"Public key not found: {key_path}")
        
        with open(key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Key is not an Ed25519 public key")
        
        return public_key
    
    def verify_license(
        self,
        license_token: str,
        module_name: str,
        odoo_version: str,
        instance_db_uuid: Optional[str] = None,
        instance_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a license token and validate business rules.
        
        Args:
            license_token: JWT license string
            module_name: Technical name of the module being verified
            odoo_version: Odoo major version (e.g., '17', '18')
            instance_db_uuid: Current instance database UUID (for fingerprint check)
            instance_domain: Current instance domain (for fingerprint check)
        
        Returns:
            Decoded and validated license payload
        
        Raises:
            LicenseVerificationError: If verification fails
        """
        try:
            # Step 1: Verify JWT signature
            payload = jwt.decode(
                license_token,
                self.public_key,
                algorithms=["EdDSA"],
                options={
                    "verify_signature": True,
                    "verify_exp": False,  # We'll handle expiration manually
                    "require": ["jti", "iss", "iat"]
                }
            )
            
            # Step 1b: Manually check expiration if present
            if "exp" in payload:
                exp_timestamp = payload["exp"]
                now_timestamp = datetime.now(timezone.utc).timestamp()
                if now_timestamp >= exp_timestamp:
                    raise jwt.ExpiredSignatureError("License has expired")
            
            # Step 2: Verify issuer
            if payload.get("iss") != self.expected_issuer:
                raise LicenseVerificationError(
                    f"Invalid issuer: expected '{self.expected_issuer}', "
                    f"got '{payload.get('iss')}'"
                )
            
            # Step 3: Verify module name
            module_info = payload.get("module", {})
            if module_info.get("technical_name") != module_name:
                raise LicenseVerificationError(
                    f"License is for module '{module_info.get('technical_name')}', "
                    f"not '{module_name}'"
                )
            
            # Step 4: Verify Odoo version
            allowed_versions = module_info.get("allowed_major_versions", [])
            if odoo_version not in allowed_versions:
                raise LicenseVerificationError(
                    f"Odoo version '{odoo_version}' not allowed. "
                    f"Allowed versions: {allowed_versions}"
                )
            
            # Step 5: Verify instance fingerprint (if license is bound)
            if "instance_fingerprint" in payload:
                if not instance_db_uuid or not instance_domain:
                    raise LicenseVerificationError(
                        "License is bound to an instance, but instance details not provided"
                    )
                
                expected_fingerprint = self._generate_fingerprint(
                    instance_db_uuid, instance_domain
                )
                
                if payload["instance_fingerprint"] != expected_fingerprint:
                    raise LicenseVerificationError(
                        f"Instance fingerprint mismatch. "
                        f"This license is bound to a different instance."
                    )
            
            # Step 6: Check license type specific rules
            license_type = payload.get("license_type")
            
            if license_type == "demo":
                # Demo licenses must have expiration
                if not payload.get("exp"):
                    raise LicenseVerificationError("Demo license must have expiration")
            
            # All checks passed
            return payload
            
        except jwt.ExpiredSignatureError:
            raise LicenseVerificationError("License has expired")
        
        except jwt.InvalidSignatureError:
            raise LicenseVerificationError("Invalid license signature - possible tampering")
        
        except jwt.DecodeError as e:
            raise LicenseVerificationError(f"License decode error: {e}")
        
        except jwt.InvalidTokenError as e:
            raise LicenseVerificationError(f"Invalid license token: {e}")
    
    def _generate_fingerprint(self, db_uuid: str, domain: str) -> str:
        """Generate instance fingerprint for comparison."""
        combined = f"{db_uuid}:{domain}".encode('utf-8')
        hash_obj = hashlib.sha256(combined)
        return f"sha256:{hash_obj.hexdigest()}"
    
    def get_license_info(self, license_token: str) -> Dict[str, Any]:
        """
        Extract license information without full validation.
        Useful for displaying license details to users.
        """
        try:
            # Decode without verification (for display purposes only)
            payload = jwt.decode(
                license_token,
                options={"verify_signature": False}
            )
            
            # Extract readable information
            info = {
                "license_id": payload.get("jti"),
                "customer": payload.get("customer", {}),
                "module": payload.get("module", {}),
                "license_type": payload.get("license_type"),
                "issued_at": self._format_timestamp(payload.get("iat")),
                "expires_at": self._format_timestamp(payload.get("exp")),
                "is_bound": "instance_fingerprint" in payload
            }
            
            return info
        
        except Exception as e:
            return {"error": f"Failed to decode license: {e}"}
    
    def _format_timestamp(self, ts: Optional[int]) -> Optional[str]:
        """Convert Unix timestamp to readable format."""
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# POC Testing / Demo
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("=" * 70)
    print("AEGIS License Verifier - POC Demo")
    print("=" * 70)
    
    # Initialize verifier with public key
    public_key_path = "keys/aegis-2026-01.public.pem"
    
    try:
        verifier = LicenseVerifier(public_key_path)
        print(f"✅ Loaded public key: {public_key_path}\n")
    except Exception as e:
        print(f"❌ Error loading public key: {e}")
        sys.exit(1)
    
    # Test cases
    test_cases = [
        {
            "name": "Valid Perpetual License",
            "license_file": "licenses/example-perpetual.jwt",
            "module": "biz4a_payroll_drc",
            "version": "17",
            "should_pass": True
        },
        {
            "name": "Valid Demo License",
            "license_file": "licenses/example-demo.jwt",
            "module": "biz4a_payroll_drc",
            "version": "18",
            "should_pass": True
        },
        {
            "name": "Wrong Module Name",
            "license_file": "licenses/example-perpetual.jwt",
            "module": "wrong_module",
            "version": "17",
            "should_pass": False
        },
        {
            "name": "Wrong Odoo Version",
            "license_file": "licenses/example-perpetual.jwt",
            "module": "biz4a_payroll_drc",
            "version": "16",  # Not in allowed_versions
            "should_pass": False
        },
        {
            "name": "Instance-Bound License (Correct)",
            "license_file": "licenses/example-bound.jwt",
            "module": "biz4a_accounting_ohada",
            "version": "17",
            "db_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "domain": "acme.odoo.com",
            "should_pass": True
        },
        {
            "name": "Instance-Bound License (Wrong Instance)",
            "license_file": "licenses/example-bound.jwt",
            "module": "biz4a_accounting_ohada",
            "version": "17",
            "db_uuid": "different-uuid",
            "domain": "wrong.odoo.com",
            "should_pass": False
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test['name']}")
        print(f"{'='*70}")
        
        # Load license token
        license_path = Path(test["license_file"])
        if not license_path.exists():
            print(f"⚠️  License file not found: {license_path}")
            continue
        
        with open(license_path, "r") as f:
            license_token = f.read().strip()
        
        # Display license info
        info = verifier.get_license_info(license_token)
        print(f"\n📋 License Info:")
        print(f"   Customer: {info.get('customer', {}).get('name')}")
        print(f"   Type: {info.get('license_type')}")
        print(f"   Issued: {info.get('issued_at')}")
        print(f"   Expires: {info.get('expires_at', 'Never')}")
        print(f"   Instance Bound: {info.get('is_bound')}")
        
        # Verify license
        print(f"\n🔍 Verification:")
        print(f"   Module: {test['module']}")
        print(f"   Odoo Version: {test['version']}")
        
        try:
            result = verifier.verify_license(
                license_token,
                module_name=test["module"],
                odoo_version=test["version"],
                instance_db_uuid=test.get("db_uuid"),
                instance_domain=test.get("domain")
            )
            
            if test["should_pass"]:
                print(f"   ✅ PASS - License verified successfully")
            else:
                print(f"   ❌ FAIL - Expected verification to fail, but it passed")
        
        except LicenseVerificationError as e:
            if not test["should_pass"]:
                print(f"   ✅ PASS - Correctly rejected: {e}")
            else:
                print(f"   ❌ FAIL - Unexpected rejection: {e}")
    
    print(f"\n{'='*70}")
    print("✅ Verification tests completed")
    print(f"{'='*70}\n")
