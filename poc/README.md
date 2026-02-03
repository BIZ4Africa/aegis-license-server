# AEGIS License Control Framework - POC

**Proof of Concept** for the AEGIS license signing and verification system.

## ✅ What This POC Demonstrates

This POC validates the complete license lifecycle:

1. **Key Generation** - Ed25519 keypair creation
2. **License Issuance** - JWT signing with EdDSA
3. **License Verification** - Offline signature validation
4. **Business Rules** - Module, version, and instance binding checks

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LICENSE SERVER                           │
│  ┌──────────────┐           ┌────────────────┐            │
│  │  Private Key │  ────────> │ License Issuer │            │
│  │ (Ed25519)    │           │  (JWT Signer)  │            │
│  └──────────────┘           └────────────────┘            │
│                                    │                        │
│                                    ▼                        │
│                           Signed JWT License                │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      │ Transfer to customer
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    ODOO CLIENT MODULE                       │
│  ┌──────────────┐           ┌────────────────┐            │
│  │  Public Key  │  ────────> │ License        │            │
│  │ (Ed25519)    │           │ Verifier       │            │
│  └──────────────┘           └────────────────┘            │
│                                    │                        │
│                                    ▼                        │
│                         ✅ Allow / ❌ Block                 │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Structure

```
aegis-poc/
├── generate_keys.py       # Ed25519 keypair generator
├── issue_license.py       # License issuer (server-side)
├── verify_license.py      # License verifier (client-side simulation)
├── requirements.txt       # Python dependencies
│
├── keys/                  # Generated keypair
│   ├── aegis-2026-01.private.pem  (🔒 SECRET - server only)
│   ├── aegis-2026-01.public.pem   (📖 public - embedded in Odoo)
│   └── aegis-2026-01.metadata.txt
│
└── licenses/              # Example licenses
    ├── example-perpetual.jwt
    ├── example-demo.jwt
    └── example-bound.jwt
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pyjwt[crypto] cryptography python-dateutil
```

### 2. Generate Keys

```bash
python generate_keys.py --key-id aegis-2026-01
```

**Output:**
- `keys/aegis-2026-01.private.pem` (119 bytes) - **KEEP SECRET**
- `keys/aegis-2026-01.public.pem` (113 bytes) - Embed in Odoo modules

### 3. Issue Licenses

```bash
python issue_license.py
```

**Generates 3 example licenses:**
- Perpetual license (no expiration)
- 30-day demo license (with expiration)
- Instance-bound perpetual license (tied to specific Odoo instance)

### 4. Verify Licenses

```bash
python verify_license.py
```

**Runs 6 test cases:**
- ✅ Valid perpetual license
- ✅ Valid demo license
- ✅ Reject wrong module name
- ✅ Reject wrong Odoo version
- ✅ Accept correct instance binding
- ✅ Reject wrong instance binding

## 📜 License Format

### JWT Structure

**Header:**
```json
{
  "alg": "EdDSA",
  "typ": "JWT",
  "kid": "aegis-2026-01"
}
```

**Payload (Perpetual License):**
```json
{
  "jti": "0bfb0cef-a864-400f-83d4-e8c6bd41dda5",
  "iss": "https://license.biz4a.com",
  "iat": 1770145930,
  "customer": {
    "id": "CUST-001",
    "name": "Acme Corporation"
  },
  "module": {
    "technical_name": "biz4a_payroll_drc",
    "allowed_major_versions": ["17", "18"]
  },
  "license_type": "perpetual"
}
```

**Signature:**
- Ed25519 signature (64 bytes)
- Base64url-encoded

### License Types

| Type | Expiration | Use Case |
|------|-----------|----------|
| `perpetual` | None | Full purchase |
| `subscription` | Required | Annual/monthly rental |
| `demo` | Required | Trial/evaluation |

## 🔒 Security Features

### Cryptography
- **Algorithm**: Ed25519 (EdDSA)
- **Key Size**: 256 bits (32 bytes)
- **Signature Size**: 64 bytes
- **Performance**: ~1ms verification time

### Validation Checks

1. **Signature Verification** - Cryptographic authenticity
2. **Issuer Check** - Must be `https://license.biz4a.com`
3. **Module Name** - License must match requested module
4. **Odoo Version** - Must be in `allowed_major_versions`
5. **Expiration** - Enforced for demo/subscription licenses
6. **Instance Binding** - Optional fingerprint verification

### Instance Fingerprinting

```python
fingerprint = sha256(f"{db_uuid}:{domain}")
# Example: sha256:cf5d28bd3758c6bac6bf0586ee15ae66bc9f26bba213c970995022fdacd661a8
```

Binds license to:
- Odoo database UUID
- Instance domain name

## 📊 Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Key Generation | ~50ms | One-time operation |
| License Issuance | ~1ms | Sign JWT |
| License Verification | ~1ms | Verify signature |
| Fingerprint Generation | <0.1ms | SHA-256 hash |

**Test Environment:** Python 3.12, Ubuntu 24.04

## 🧪 Test Coverage

```bash
python verify_license.py
```

**Test Matrix:**

| Test | Module | Version | Instance | Expected |
|------|--------|---------|----------|----------|
| Valid Perpetual | ✅ | ✅ | N/A | ✅ Pass |
| Valid Demo | ✅ | ✅ | N/A | ✅ Pass |
| Wrong Module | ❌ | ✅ | N/A | ✅ Reject |
| Wrong Version | ✅ | ❌ | N/A | ✅ Reject |
| Correct Instance | ✅ | ✅ | ✅ | ✅ Pass |
| Wrong Instance | ✅ | ✅ | ❌ | ✅ Reject |

All tests passing ✅

## 🔄 Integration with Odoo

### Server-Side (License Authority)

```python
from issue_license import LicenseIssuer

issuer = LicenseIssuer("keys/aegis-2026-01.private.pem")

license_token = issuer.issue_license(
    customer_id="CUST-001",
    customer_name="Acme Corp",
    module_name="biz4a_payroll_drc",
    allowed_versions=["17", "18"],
    license_type="perpetual"
)

# Send token to customer
```

### Client-Side (Odoo Module)

```python
# In __manifest__.py or module init
from verify_license import LicenseVerifier

verifier = LicenseVerifier("public_keys/aegis-2026-01.public.pem")

try:
    verifier.verify_license(
        license_token=license_from_config,
        module_name="biz4a_payroll_drc",
        odoo_version=odoo.release.major_version
    )
except LicenseVerificationError as e:
    raise Exception(f"License validation failed: {e}")
```

## 📋 Next Steps

### Immediate
- [ ] Create REST API wrapper for license issuance
- [ ] Implement license database (PostgreSQL)
- [ ] Add license revocation mechanism
- [ ] Create admin interface for license management

### Short-term
- [ ] Implement key rotation strategy
- [ ] Add online validation endpoint (optional)
- [ ] Create license inspection CLI tool
- [ ] Build customer portal for license download

### Medium-term
- [ ] Docker deployment configuration
- [ ] CI/CD pipeline
- [ ] Monitoring and alerting
- [ ] Backup and disaster recovery procedures

## 🛡️ Security Considerations

### ⚠️ Current POC Limitations

- Private key is **NOT encrypted** (use KMS in production)
- No rate limiting on verification
- No audit logging
- No license revocation mechanism

### 🔐 Production Recommendations

1. **Key Storage**
   - Use AWS KMS, Azure Key Vault, or HashiCorp Vault
   - Never commit private keys to version control
   - Implement key rotation every 12 months

2. **Monitoring**
   - Log all license issuance events
   - Alert on verification failures
   - Track license usage patterns

3. **Backup**
   - Encrypted backups of private keys
   - Offline storage in multiple locations
   - Regular recovery drills

## 📚 References

- [ADR-0001: License Signing Algorithm](../ADR-0001-license-signing.md)
- [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 8032: EdDSA](https://datatracker.ietf.org/doc/html/rfc8032)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

## 📄 License

Proprietary - Business Solutions For Africa (BIZ4A)  
© 2026 BIZ4A - All rights reserved.

---

**Maintainer:** BIZ4A Technical Team  
**Status:** POC - Not production ready  
**Last Updated:** 2026-02-03
