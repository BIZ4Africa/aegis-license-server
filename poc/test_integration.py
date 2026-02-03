#!/usr/bin/env python3
"""
AEGIS POC - Complete Integration Test

Tests the full license lifecycle:
1. Key generation
2. License issuance
3. License verification
4. Edge cases and error handling
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Import our modules
from generate_keys import generate_keypair
from issue_license import LicenseIssuer, generate_instance_fingerprint
from verify_license import LicenseVerifier, LicenseVerificationError


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name: str):
        self.total += 1
        self.passed += 1
        print(f"  ✅ {test_name}")
    
    def add_fail(self, test_name: str, reason: str):
        self.total += 1
        self.failed += 1
        self.errors.append((test_name, reason))
        print(f"  ❌ {test_name}: {reason}")
    
    def summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for test, reason in self.errors:
                print(f"  - {test}: {reason}")
            return False
        else:
            print("\n🎉 All tests passed!")
            return True


def run_integration_test():
    """Run complete integration test suite."""
    
    results = TestResults()
    
    print("=" * 70)
    print("AEGIS POC - Integration Test Suite")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    # Use temporary directory for test keys
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # ================================================================
        # TEST SUITE 1: Key Generation
        # ================================================================
        print("\n📝 Test Suite 1: Key Generation")
        print("-" * 70)
        
        try:
            private_key_path, public_key_path = generate_keypair(
                "test-key-01",
                output_dir=temp_dir
            )
            
            # Verify files exist
            if Path(private_key_path).exists():
                results.add_pass("Private key file created")
            else:
                results.add_fail("Private key file created", "File not found")
            
            if Path(public_key_path).exists():
                results.add_pass("Public key file created")
            else:
                results.add_fail("Public key file created", "File not found")
            
            # Verify file sizes (Ed25519 keys are small)
            private_size = Path(private_key_path).stat().st_size
            public_size = Path(public_key_path).stat().st_size
            
            if private_size > 0 and private_size < 200:
                results.add_pass("Private key size valid")
            else:
                results.add_fail("Private key size valid", f"Size: {private_size}")
            
            if public_size > 0 and public_size < 200:
                results.add_pass("Public key size valid")
            else:
                results.add_fail("Public key size valid", f"Size: {public_size}")
        
        except Exception as e:
            results.add_fail("Key generation", str(e))
            return results  # Can't continue without keys
        
        # ================================================================
        # TEST SUITE 2: License Issuance
        # ================================================================
        print("\n📝 Test Suite 2: License Issuance")
        print("-" * 70)
        
        try:
            issuer = LicenseIssuer(private_key_path, key_id="test-key-01")
            results.add_pass("Initialize license issuer")
        except Exception as e:
            results.add_fail("Initialize license issuer", str(e))
            return results
        
        # Test perpetual license
        try:
            perpetual = issuer.issue_license(
                customer_id="TEST-001",
                customer_name="Test Customer",
                module_name="test_module",
                allowed_versions=["17"],
                license_type="perpetual"
            )
            
            if perpetual and len(perpetual) > 100:
                results.add_pass("Issue perpetual license")
            else:
                results.add_fail("Issue perpetual license", "Invalid token")
        except Exception as e:
            results.add_fail("Issue perpetual license", str(e))
        
        # Test demo license
        try:
            demo = issuer.issue_license(
                customer_id="DEMO-001",
                customer_name="Demo Customer",
                module_name="test_module",
                allowed_versions=["17"],
                license_type="demo",
                duration_days=30
            )
            
            if demo and len(demo) > 100:
                results.add_pass("Issue demo license")
            else:
                results.add_fail("Issue demo license", "Invalid token")
        except Exception as e:
            results.add_fail("Issue demo license", str(e))
        
        # Test instance-bound license
        try:
            fingerprint = generate_instance_fingerprint(
                "test-db-uuid",
                "test.odoo.com"
            )
            
            bound = issuer.issue_license(
                customer_id="TEST-002",
                customer_name="Test Customer 2",
                module_name="test_module",
                allowed_versions=["17"],
                license_type="perpetual",
                instance_fingerprint=fingerprint
            )
            
            if bound and len(bound) > 100:
                results.add_pass("Issue instance-bound license")
            else:
                results.add_fail("Issue instance-bound license", "Invalid token")
        except Exception as e:
            results.add_fail("Issue instance-bound license", str(e))
        
        # Test invalid license type
        try:
            issuer.issue_license(
                customer_id="TEST-003",
                customer_name="Test",
                module_name="test",
                allowed_versions=["17"],
                license_type="invalid_type"
            )
            results.add_fail("Reject invalid license type", "Should have raised error")
        except ValueError:
            results.add_pass("Reject invalid license type")
        except Exception as e:
            results.add_fail("Reject invalid license type", f"Wrong error: {e}")
        
        # ================================================================
        # TEST SUITE 3: License Verification
        # ================================================================
        print("\n📝 Test Suite 3: License Verification")
        print("-" * 70)
        
        try:
            verifier = LicenseVerifier(public_key_path)
            results.add_pass("Initialize license verifier")
        except Exception as e:
            results.add_fail("Initialize license verifier", str(e))
            return results
        
        # Test valid perpetual license
        try:
            verifier.verify_license(
                perpetual,
                module_name="test_module",
                odoo_version="17"
            )
            results.add_pass("Verify valid perpetual license")
        except Exception as e:
            results.add_fail("Verify valid perpetual license", str(e))
        
        # Test valid demo license
        try:
            verifier.verify_license(
                demo,
                module_name="test_module",
                odoo_version="17"
            )
            results.add_pass("Verify valid demo license")
        except Exception as e:
            results.add_fail("Verify valid demo license", str(e))
        
        # Test wrong module name
        try:
            verifier.verify_license(
                perpetual,
                module_name="wrong_module",
                odoo_version="17"
            )
            results.add_fail("Reject wrong module", "Should have raised error")
        except LicenseVerificationError:
            results.add_pass("Reject wrong module")
        except Exception as e:
            results.add_fail("Reject wrong module", f"Wrong error: {e}")
        
        # Test wrong version
        try:
            verifier.verify_license(
                perpetual,
                module_name="test_module",
                odoo_version="16"
            )
            results.add_fail("Reject wrong version", "Should have raised error")
        except LicenseVerificationError:
            results.add_pass("Reject wrong version")
        except Exception as e:
            results.add_fail("Reject wrong version", f"Wrong error: {e}")
        
        # Test correct instance binding
        try:
            verifier.verify_license(
                bound,
                module_name="test_module",
                odoo_version="17",
                instance_db_uuid="test-db-uuid",
                instance_domain="test.odoo.com"
            )
            results.add_pass("Accept correct instance binding")
        except Exception as e:
            results.add_fail("Accept correct instance binding", str(e))
        
        # Test wrong instance binding
        try:
            verifier.verify_license(
                bound,
                module_name="test_module",
                odoo_version="17",
                instance_db_uuid="wrong-uuid",
                instance_domain="wrong.odoo.com"
            )
            results.add_fail("Reject wrong instance", "Should have raised error")
        except LicenseVerificationError:
            results.add_pass("Reject wrong instance")
        except Exception as e:
            results.add_fail("Reject wrong instance", f"Wrong error: {e}")
        
        # ================================================================
        # TEST SUITE 4: Tampering Detection
        # ================================================================
        print("\n📝 Test Suite 4: Tampering Detection")
        print("-" * 70)
        
        # Test tampered signature
        try:
            tampered = perpetual[:-10] + "TAMPERED!"
            verifier.verify_license(
                tampered,
                module_name="test_module",
                odoo_version="17"
            )
            results.add_fail("Detect tampered signature", "Should have raised error")
        except (LicenseVerificationError, Exception):
            results.add_pass("Detect tampered signature")
        
        # Test corrupted payload
        try:
            parts = perpetual.split('.')
            if len(parts) == 3:
                corrupted = parts[0] + ".CORRUPTED." + parts[2]
                verifier.verify_license(
                    corrupted,
                    module_name="test_module",
                    odoo_version="17"
                )
                results.add_fail("Detect corrupted payload", "Should have raised error")
            else:
                results.add_fail("Detect corrupted payload", "Invalid token format")
        except (LicenseVerificationError, Exception):
            results.add_pass("Detect corrupted payload")
        
        # ================================================================
        # TEST SUITE 5: Edge Cases
        # ================================================================
        print("\n📝 Test Suite 5: Edge Cases")
        print("-" * 70)
        
        # Test empty token
        try:
            verifier.verify_license(
                "",
                module_name="test_module",
                odoo_version="17"
            )
            results.add_fail("Reject empty token", "Should have raised error")
        except (LicenseVerificationError, Exception):
            results.add_pass("Reject empty token")
        
        # Test malformed token
        try:
            verifier.verify_license(
                "not.a.jwt",
                module_name="test_module",
                odoo_version="17"
            )
            results.add_fail("Reject malformed token", "Should have raised error")
        except (LicenseVerificationError, Exception):
            results.add_pass("Reject malformed token")
        
        # Test get_license_info
        try:
            info = verifier.get_license_info(perpetual)
            if "license_id" in info and "customer" in info:
                results.add_pass("Extract license info")
            else:
                results.add_fail("Extract license info", "Missing fields")
        except Exception as e:
            results.add_fail("Extract license info", str(e))
    
    # Return results
    return results


def main():
    """Main entry point."""
    results = run_integration_test()
    success = results.summary()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
