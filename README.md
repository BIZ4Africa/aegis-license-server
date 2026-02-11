# AEGIS License Server v0.8.0

Production-ready license management API for AEGIS-protected Odoo modules.

Built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, and **Ed25519** cryptographic signing.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Option 1: Easy Deployment (Recommended)

```bash
# One command deployment
./deploy/deploy.sh
```

This helper will:
- create `.env` from `.env.example` if missing
- generate signing keys if missing
- build and start Docker services
- run a health check automatically

For manual Docker usage, see `docs/deployment-runbook.md`.

### Option 2: Local Development

```bash
# 1. Install dependencies
cd server/
pip install -r requirements.txt

# 2. Generate keys
python ../scripts/generate_keys.py

# 3. Configure environment
cp ../.env.example ../.env
# Edit .env with your database credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start server
uvicorn server.main:app --reload
```

API Documentation: http://localhost:8000/docs

---

## 📋 Features

### Core Capabilities

✅ **License Management**
- Issue perpetual, subscription, and demo licenses
- Cryptographic JWT signing with Ed25519
- Instance binding via fingerprints
- License revocation

✅ **Customer Management**
- CRUD operations for customers
- License assignment tracking
- Activity status management

✅ **Validation & Security**
- Offline-first license verification
- Signature tampering detection
- Expiration enforcement
- Version compatibility checks

✅ **Audit & Monitoring**
- Complete audit trail of all operations
- Usage statistics and analytics
- Health check endpoints

### API Endpoints

**Licenses:**
- `POST /api/v1/licenses` - Issue a new license
- `GET /api/v1/licenses/{id}` - Get license details
- `GET /api/v1/licenses` - List licenses (with filters)
- `POST /api/v1/licenses/validate` - Validate a license token
- `DELETE /api/v1/licenses/{id}/revoke` - Revoke a license
- `POST /api/v1/licenses/fingerprint` - Generate instance fingerprint

**Customers:**
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer
- `GET /api/v1/customers` - List customers
- `PATCH /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

**Admin:**
- `GET /api/v1/admin/stats` - Server statistics
- `GET /api/v1/admin/audit-logs` - Audit logs

**System:**
- `GET /health` - Health check
- `GET /info` - Server information

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.109 | REST API with automatic docs |
| **Database** | PostgreSQL 15 | Relational data storage |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Migrations** | Alembic | Schema versioning |
| **Crypto** | PyJWT + Ed25519 | License signing |
| **Validation** | Pydantic 2.5 | Request/response validation |
| **Logging** | Structlog | Structured JSON logging |
| **Server** | Uvicorn | ASGI server |

### Database Schema

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│  customers  │       │   licenses   │       │ audit_logs  │
├─────────────┤       ├──────────────┤       ├─────────────┤
│ id (PK)     │───┐   │ id (PK)      │   ┌───│ id (PK)     │
│ name        │   └───│ customer_id  │───┘   │ license_id  │
│ email       │       │ module_name  │       │ event_type  │
│ company     │       │ license_type │       │ customer_id │
│ is_active   │       │ status       │       │ event_data  │
│ created_at  │       │ token (JWT)  │       │ created_at  │
└─────────────┘       │ expires_at   │       └─────────────┘
                      │ revoked_at   │
                      └──────────────┘
```

### License JWT Structure

**Header:**
```json
{
  "alg": "EdDSA",
  "typ": "JWT",
  "kid": "aegis-2026-01"
}
```

**Payload:**
```json
{
  "jti": "uuid",
  "iss": "https://license.biz4a.com",
  "iat": 1738588800,
  "exp": null,
  "customer": {
    "id": "CUST-001",
    "name": "Acme Corp"
  },
  "module": {
    "technical_name": "biz4a_payroll_drc",
    "allowed_major_versions": ["17", "18"]
  },
  "license_type": "perpetual"
}
```

---

## 🔐 Security

### Key Management

**Private Key:**
- Generated with Ed25519 algorithm
- Stored in `keys/aegis-{year}-{version}.private.pem`
- **CRITICAL:** Never commit to version control
- Permissions: 0600 (owner read/write only)
- Production: Use KMS (AWS KMS, Azure Key Vault, HashiCorp Vault)

**Public Key:**
- Stored in `keys/aegis-{year}-{version}.public.pem`
- Distributed to Odoo clients
- Can be safely committed to version control
- Embedded in AEGIS client modules

### Key Rotation

```bash
# Generate new keypair
python scripts/generate_keys.py --key-id aegis-2027-01

# Update .env
KEY_ID=aegis-2027-01
PRIVATE_KEY_PATH=keys/aegis-2027-01.private.pem

# Restart server
# Old licenses remain valid (verified with old public key)
```

### Environment Variables

**Critical Security Settings:**

```bash
# Strong random secret (64+ characters)
API_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Database credentials
DATABASE_URL=postgresql+asyncpg://user:STRONG_PASSWORD@host/db

# Key paths
PRIVATE_KEY_PATH=keys/aegis-2026-01.private.pem
```

---

## 📊 Operations

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current version
alembic current
```

### Health Monitoring

```bash
# Health check
curl http://localhost:8000/health

# Statistics
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/admin/stats
```

### Logs

```bash
# Development (text format)
LOG_FORMAT=text LOG_LEVEL=DEBUG uvicorn server.main:app

# Production (JSON format)
LOG_FORMAT=json LOG_LEVEL=INFO uvicorn server.main:app
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=server --cov-report=html

# Specific test file
pytest tests/test_licenses.py -v
```

---

## 📦 Deployment

### Production Checklist

- [ ] Generate strong API secret key
- [ ] Configure secure database credentials
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Store private keys in KMS or encrypted storage
- [ ] Configure CORS origins
- [ ] Enable rate limiting
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Set up automated backups (database + keys)
- [ ] Test disaster recovery procedures

### Docker Production

```bash
# Deploy complete stack (API + PostgreSQL)
./deploy/deploy.sh

# Or manually
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

Detailed procedures (operations, upgrades, troubleshooting):
- `docs/deployment-runbook.md`

### Kubernetes

Not yet provided in this phase.

---

## 📖 API Usage Examples

### Issue a Perpetual License

```bash
curl -X POST http://localhost:8000/api/v1/licenses \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "customer_id": "CUST-001",
    "module_name": "biz4a_payroll_drc",
    "allowed_major_versions": ["17", "18"],
    "license_type": "perpetual"
  }'
```

### Validate a License

```bash
curl -X POST http://localhost:8000/api/v1/licenses/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGc...",
    "module_name": "biz4a_payroll_drc",
    "odoo_version": "17"
  }'
```

### Revoke a License

```bash
curl -X DELETE http://localhost:8000/api/v1/licenses/{id}/revoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "reason": "Customer requested cancellation"
  }'
```

---

## 🛠️ Development

### Project Structure

```
aegis-server/
├── server/                  # Main application code
│   ├── main.py             # FastAPI app
│   ├── config.py           # Configuration
│   ├── database.py         # Database connection
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── services.py         # Business logic
│   └── routers/            # API routes
│       ├── health.py
│       ├── licenses.py
│       ├── customers.py
│       └── admin.py
├── alembic/                # Database migrations
├── scripts/                # Utility scripts
├── deploy/                 # Deployment files
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                  # Test suite
└── keys/                   # Cryptographic keys (gitignored)
```

### Code Quality

```bash
# Format code
black server/

# Lint
ruff check server/

# Type check
mypy server/
```

---

## 📚 Related Documentation

- [ADR-0001: License Signing Algorithm](/docs/adr/ADR-0001-license-signing.md)
- [POC Documentation](/poc/README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)

---

## 🆘 Troubleshooting

### Common Issues

**Error: "Private key not found"**
```bash
# Generate keys first
python scripts/generate_keys.py
```

**Error: "Connection refused" (database)**
```bash
# Check PostgreSQL is running
docker-compose ps

# Check connection string
echo $DATABASE_URL
```

**Error: "Invalid API Key"**
```bash
# API authentication not implemented yet
# Will be added in next release
```

---

## 📝 License

Proprietary - Business Solutions For Africa (BIZ4A)  
© 2026 BIZ4A - All rights reserved.

---

## 👥 Maintainers

**BIZ4A Technical Team**  
Digital Transformation & Enterprise Solutions

For support: tech@biz4a.com

---

**Version:** 0.8.0
**Last Updated:** 2026-02-10
