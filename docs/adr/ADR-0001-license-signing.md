# ADR-0001: License Signing Algorithm and Format

**Status:** Accepted  
**Date:** 2026-02-03  
**Deciders:** BIZ4A Technical Team  
**Context:** AEGIS License Control Framework

---

## Context and Problem Statement

AEGIS requires cryptographic signing of license payloads to ensure:
- **Authenticity**: Licenses are issued only by BIZ4A's license server
- **Integrity**: License content cannot be tampered with
- **Non-repudiation**: Issued licenses can be proven legitimate

The signing mechanism must work in:
- **Offline environments** (primary use case)
- **Low-resource Odoo.sh instances**
- **On-premise deployments** with varying Python versions

Key requirements:
1. Signature verification must be fast (<10ms per license)
2. Public key embedding in Odoo client must be straightforward
3. Algorithm must be widely supported (Python 3.8+, standard libraries preferred)
4. Format must be human-readable for debugging
5. No reliance on external validation services for core functionality

---

## Decision Drivers

- **Security**: Resistance to known cryptographic attacks
- **Performance**: Fast verification on low-end hardware
- **Compatibility**: Works across Odoo.sh, Python 3.8-3.12
- **Maintainability**: Well-documented, standard implementation
- **Simplicity**: Minimal dependencies, clear security model
- **Future-proofing**: Algorithm longevity (10+ years)

---

## Considered Options

### Option 1: RSA-PSS (4096-bit)
- **Algorithm**: RSA with PSS padding
- **Key size**: 4096 bits
- **Hash**: SHA-256
- **Format**: Custom JSON + Base64 signature

**Pros:**
- Industry standard, universally supported
- Strong security track record
- Well-understood by auditors/legal teams

**Cons:**
- Large key sizes (public key ~550 bytes)
- Slower signature generation (~50ms)
- Verification still performant (~3ms)

---

### Option 2: Ed25519 (EdDSA)
- **Algorithm**: Edwards-curve Digital Signature Algorithm
- **Curve**: Curve25519
- **Hash**: Built-in (SHA-512 internally)
- **Format**: Custom JSON + Base64 signature

**Pros:**
- Extremely fast (sign: 0.5ms, verify: 1ms)
- Small keys (public: 32 bytes, private: 32 bytes)
- Modern, secure design (resists timing attacks)
- Native support in Python 3.9+ (`cryptography` library)

**Cons:**
- Less familiar to non-cryptographers
- Requires `cryptography` library (not in stdlib)

---

### Option 3: JSON Web Tokens (JWT with RS256 or EdDSA)
- **Standard**: RFC 7519 (JWT)
- **Algorithms**: RS256 (RSA-SHA256) or EdDSA
- **Format**: Standard JWT structure

**Pros:**
- Industry-standard format
- Built-in expiration handling (`exp` claim)
- Extensive tooling (validators, debuggers like jwt.io)
- Libraries: PyJWT, python-jose

**Cons:**
- Adds payload size overhead (~30%)
- Some features unused (nested claims, multiple audiences)
- Still requires choosing underlying algorithm (RS256 vs EdDSA)

---

## Decision

**Selected Option: JSON Web Tokens (JWT) with EdDSA (Ed25519)**

### Rationale

We combine the best of Options 2 and 3:

1. **Format**: Use **JWT (RFC 7519)** as the container format
   - Provides standard structure (`header.payload.signature`)
   - Leverages existing ecosystem tooling
   - Clear separation of concerns (header metadata, payload data, signature)

2. **Algorithm**: Use **EdDSA with Ed25519** as the signing algorithm
   - Superior performance for signature verification (critical path)
   - Compact public keys (easy to embed in Odoo modules)
   - Modern cryptographic standard (FIPS 186-5)

### Implementation Details

#### Library
- **Python**: `PyJWT` (pip install pyjwt[crypto])
- **Algorithm identifier**: `EdDSA`

#### JWT Structure

**Header:**
```json
{
  "alg": "EdDSA",
  "typ": "JWT",
  "kid": "aegis-2026-01"  // Key ID for rotation support
}
```

**Payload (Claims):**
```json
{
  "jti": "550e8400-e29b-41d4-a716-446655440000",  // JWT ID = license_id
  "iss": "https://license.biz4a.com",             // Issuer
  "iat": 1738588800,                               // Issued At (Unix timestamp)
  "exp": null,                                     // Expiration (null for perpetual)
  
  "customer": {
    "id": "CUST-001",
    "name": "Acme Corp"
  },
  "module": {
    "technical_name": "biz4a_payroll_drc",
    "allowed_major_versions": ["17", "18"]
  },
  "license_type": "perpetual",                     // perpetual | subscription | demo
  "instance_fingerprint": "sha256:abcdef123456"    // Optional binding
}
```

**Signature:**
- Ed25519 signature of `base64url(header).base64url(payload)`
- Encoded as base64url per JWT spec

#### Final Token Format
```
eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCIsImtpZCI6ImFlZ2lzLTIwMjYtMDEifQ.eyJqdGkiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJpc3MiOiJodHRwczovL2xpY2Vuc2UuYml6NGEuY29tIiwiaWF0IjoxNzM4NTg4ODAwLCJleHAiOm51bGwsImN1c3RvbWVyIjp7ImlkIjoiQ1VTVC0wMDEiLCJuYW1lIjoiQWNtZSBDb3JwIn0sIm1vZHVsZSI6eyJ0ZWNobmljYWxfbmFtZSI6ImJpejRhX3BheXJvbGxfZHJjIiwiYWxsb3dlZF9tYWpvcl92ZXJzaW9ucyI6WyIxNyIsIjE4Il19LCJsaWNlbnNlX3R5cGUiOiJwZXJwZXR1YWwiLCJpbnN0YW5jZV9maW5nZXJwcmludCI6InNoYTI1NjphYmNkZWYxMjM0NTYifQ.signature_here
```

#### Key Management

**Private Key (Server-side only):**
- Stored in environment variable or secure file
- Format: PEM-encoded Ed25519 private key
- Rotation strategy: `kid` header tracks active key version

**Public Key (Embedded in Odoo Client):**
- Stored in `aegis_client/security/public_keys/`
- Format: PEM-encoded Ed25519 public key
- Multiple keys supported (identified by `kid`)

```python
# Example public key file: aegis-2026-01.pub.pem
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA... (32 bytes base64)
-----END PUBLIC KEY-----
```

---

## Consequences

### Positive

✅ **Performance**: Verification completes in ~1ms (100x faster than RSA)  
✅ **Compatibility**: Works on all target platforms (Python 3.8+ with `cryptography`)  
✅ **Debuggability**: JWT format is human-readable, tools like jwt.io work out-of-box  
✅ **Security**: Ed25519 is quantum-resistant for current threat models, no known weaknesses  
✅ **Key Rotation**: `kid` header enables seamless key rotation without breaking existing licenses  
✅ **Compact**: Small public keys (~44 bytes base64) minimize Odoo module size  

### Negative

⚠️ **Dependency**: Requires `PyJWT` and `cryptography` libraries (not stdlib)  
⚠️ **Novelty**: Ed25519 less familiar than RSA to some stakeholders  
⚠️ **Migration**: If switching from prototype RSA implementation, requires re-signing all licenses  

### Neutral

🔄 **Token Size**: JWT overhead adds ~20-30% vs raw JSON, but still <2KB per license  
🔄 **Validation**: Client must validate both signature AND business rules (expiration, version compatibility)  

---

## Implementation Checklist

- [ ] Install dependencies: `pip install pyjwt[crypto]`
- [ ] Generate initial Ed25519 keypair (`aegis-2026-01`)
- [ ] Implement server-side license signing (`/licenses/issue` endpoint)
- [ ] Implement client-side signature verification (Odoo module init)
- [ ] Add `kid`-based key rotation logic
- [ ] Document key backup and recovery procedures
- [ ] Add signature verification to CI/CD tests
- [ ] Create license inspection CLI tool for debugging

---

## References

- [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)](https://datatracker.ietf.org/doc/html/rfc8032)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Ed25519 Performance Benchmarks](https://bench.cr.yp.to/results-sign.html)
- [NIST FIPS 186-5: Digital Signature Standard](https://csrc.nist.gov/publications/detail/fips/186/5/final)

---

## Revision History

| Date       | Version | Changes                          |
|------------|---------|----------------------------------|
| 2026-02-03 | 1.0     | Initial decision (JWT + EdDSA)   |
