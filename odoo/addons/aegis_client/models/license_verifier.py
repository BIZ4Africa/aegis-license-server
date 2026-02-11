import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class LicenseVerificationError(Exception):
    """Raised when license verification fails."""


class LicenseVerifier:
    """Verifies AEGIS license signatures and business rules."""

    def __init__(self, public_key_path: str, expected_issuer: str):
        self.public_key = self._load_public_key(public_key_path)
        self.expected_issuer = expected_issuer

    def _load_public_key(self, key_path: str) -> ed25519.Ed25519PublicKey:
        key_path_obj = Path(key_path)
        if not key_path_obj.exists():
            raise FileNotFoundError(f"Public key not found: {key_path}")

        with open(key_path, "rb") as handle:
            public_key = serialization.load_pem_public_key(handle.read())

        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Key is not an Ed25519 public key")

        return public_key

    def verify_license(
        self,
        license_token: str,
        module_name: str,
        odoo_version: str,
        instance_db_uuid: Optional[str] = None,
        instance_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                license_token,
                self.public_key,
                algorithms=["EdDSA"],
                options={
                    "verify_signature": True,
                    "verify_exp": False,
                    "require": ["jti", "iss", "iat"],
                },
            )

            if "exp" in payload:
                exp_timestamp = payload["exp"]
                now_timestamp = datetime.now(timezone.utc).timestamp()
                if now_timestamp >= exp_timestamp:
                    raise jwt.ExpiredSignatureError("License has expired")

            if payload.get("iss") != self.expected_issuer:
                raise LicenseVerificationError(
                    f"Invalid issuer: expected '{self.expected_issuer}', got '{payload.get('iss')}'"
                )

            module_info = payload.get("module", {})
            if module_info.get("technical_name") != module_name:
                raise LicenseVerificationError(
                    "License is for module '%s', not '%s'"
                    % (module_info.get("technical_name"), module_name)
                )

            allowed_versions = module_info.get("allowed_major_versions", [])
            if odoo_version not in allowed_versions:
                raise LicenseVerificationError(
                    "Odoo version '%s' not allowed. Allowed versions: %s"
                    % (odoo_version, allowed_versions)
                )

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
                        "Instance fingerprint mismatch. This license is bound to a different instance."
                    )

            license_type = payload.get("license_type")
            if license_type == "demo" and not payload.get("exp"):
                raise LicenseVerificationError("Demo license must have expiration")

            return payload

        except jwt.ExpiredSignatureError:
            raise LicenseVerificationError("License has expired")

        except jwt.InvalidSignatureError:
            raise LicenseVerificationError("Invalid license signature - possible tampering")

        except jwt.DecodeError as exc:
            raise LicenseVerificationError(f"License decode error: {exc}")

        except jwt.InvalidTokenError as exc:
            raise LicenseVerificationError(f"Invalid license token: {exc}")

    def get_license_info(self, license_token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(license_token, options={"verify_signature": False})
            return {
                "license_id": payload.get("jti"),
                "customer": payload.get("customer", {}),
                "module": payload.get("module", {}),
                "license_type": payload.get("license_type"),
                "issued_at": self._format_timestamp(payload.get("iat")),
                "expires_at": self._format_timestamp(payload.get("exp")),
                "is_bound": "instance_fingerprint" in payload,
            }
        except Exception as exc:
            return {"error": f"Failed to decode license: {exc}"}

    def _format_timestamp(self, ts: Optional[int]) -> Optional[str]:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def _generate_fingerprint(self, db_uuid: str, domain: str) -> str:
        combined = f"{db_uuid}:{domain}".encode("utf-8")
        hash_obj = hashlib.sha256(combined)
        return f"sha256:{hash_obj.hexdigest()}"
