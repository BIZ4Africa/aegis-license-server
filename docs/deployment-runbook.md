# Deployment Runbook (Docker)

This runbook provides a **simple and repeatable** deployment workflow for the AEGIS License Server.

## 1) Prerequisites

- Docker Engine 24+
- Docker Compose plugin (`docker compose`)
- Python 3.11+ (only needed to generate signing keys)

## 2) One-command deployment (recommended)

From repository root:

```bash
./deploy/deploy.sh
```

What this does automatically:

1. Creates `.env` from `.env.example` if missing.
2. Generates Ed25519 keys in `keys/` if missing.
3. Builds and starts the production stack.
4. Runs health checks.

### Useful options

```bash
# Custom key id
./deploy/deploy.sh --key-id aegis-2026-02

# Skip image build
./deploy/deploy.sh --no-build

# Fail if keys do not already exist
./deploy/deploy.sh --skip-keygen
```

## 3) Manual deployment flow

If you prefer full control:

```bash
cp .env.example .env
# Edit .env and replace all CHANGE_ME values

python scripts/generate_keys.py --key-id aegis-2026-01

docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

## 4) Validate the deployment

```bash
# Service status
docker compose -f deploy/docker-compose.prod.yml ps

# API health
curl http://localhost:8000/health

# API metadata
curl http://localhost:8000/info
```

## 5) Operations

### View logs

```bash
# All services
docker compose -f deploy/docker-compose.prod.yml logs -f

# API only
docker compose -f deploy/docker-compose.prod.yml logs -f api
```

### Restart services

```bash
docker compose -f deploy/docker-compose.prod.yml restart
```

### Stop services

```bash
docker compose -f deploy/docker-compose.prod.yml down
```

### Upgrade to a new version

```bash
git pull
./deploy/deploy.sh
```

## 6) Required environment values before production

At minimum, review these values in `.env`:

- `POSTGRES_PASSWORD`
- `API_SECRET_KEY`
- `PRIVATE_KEY_PASSPHRASE`
- `CORS_ORIGINS`
- `LICENSE_ISSUER`

> Do not keep defaults in production.

## 7) Security notes

- Keep `keys/*.private.pem` secret (chmod 600).
- Never commit `.env` or private keys.
- Restrict host firewall to required ports only.
- Prefer TLS termination via reverse proxy (Nginx/Traefik).

## 8) Troubleshooting

### API health check fails

```bash
docker compose -f deploy/docker-compose.prod.yml logs api --tail 200
```

Common causes:
- Wrong `DATABASE_URL` / DB credentials.
- Missing private key files in `keys/`.
- Invalid environment values in `.env`.

### Database not reachable

```bash
docker compose -f deploy/docker-compose.prod.yml logs db --tail 100
```

Check:
- `POSTGRES_PASSWORD` is set.
- No port conflicts on 5432.
