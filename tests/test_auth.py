"""
AEGIS License Server - Authentication Tests
Tests for API key authentication and authorization.
"""

import pytest
from httpx import AsyncClient

from server.config import settings
from server.dependencies import generate_plain_api_key, hash_api_key
from server.models import APIKey


pytestmark = pytest.mark.asyncio


# ===== Unauthenticated Access Tests =====

async def test_health_endpoint_no_auth_required(client: AsyncClient):
    """Health endpoint should be accessible without an API key."""
    response = await client.get("/health")
    assert response.status_code == 200


async def test_validate_endpoint_no_auth_required(client: AsyncClient):
    """License validation endpoint is public (called by Odoo instances)."""
    # Even with an invalid token, the endpoint must not return 401
    response = await client.post(
        "/api/v1/licenses/validate",
        json={
            "token": "invalid.token.value",
            "module_name": "my_module",
            "odoo_version": "17",
        },
    )
    # Should return 200 with valid=False, not 401
    assert response.status_code == 200
    assert response.json()["valid"] is False


async def test_fingerprint_endpoint_no_auth_required(client: AsyncClient):
    """Fingerprint generation is a utility endpoint, no auth required."""
    response = await client.post(
        "/api/v1/licenses/fingerprint",
        json={"db_uuid": "test-uuid-1234", "domain": "example.com"},
    )
    assert response.status_code == 200


# ===== Missing API Key Tests =====

async def test_list_licenses_requires_auth(client: AsyncClient):
    """GET /api/v1/licenses should return 422 when X-API-Key header is missing."""
    response = await client.get("/api/v1/licenses")
    assert response.status_code == 422


async def test_list_customers_requires_auth(client: AsyncClient):
    """GET /api/v1/customers should return 422 when X-API-Key header is missing."""
    response = await client.get("/api/v1/customers")
    assert response.status_code == 422


async def test_admin_stats_requires_auth(client: AsyncClient):
    """GET /api/v1/admin/stats should return 422 when X-API-Key header is missing."""
    response = await client.get("/api/v1/admin/stats")
    assert response.status_code == 422


async def test_admin_audit_logs_requires_auth(client: AsyncClient):
    """GET /api/v1/admin/audit-logs should return 422 when X-API-Key header is missing."""
    response = await client.get("/api/v1/admin/audit-logs")
    assert response.status_code == 422


# ===== Invalid API Key Tests =====

async def test_list_licenses_invalid_key_returns_401(client: AsyncClient):
    """Invalid API key should return 401 Unauthorized."""
    response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": "invalid-key-value"},
    )
    assert response.status_code == 401


async def test_list_customers_invalid_key_returns_401(client: AsyncClient):
    """Invalid API key should return 401 Unauthorized."""
    response = await client.get(
        "/api/v1/customers",
        headers={"X-API-Key": "invalid-key-value"},
    )
    assert response.status_code == 401


async def test_admin_stats_invalid_key_returns_401(client: AsyncClient):
    """Invalid API key should return 401 Unauthorized."""
    response = await client.get(
        "/api/v1/admin/stats",
        headers={"X-API-Key": "invalid-key-value"},
    )
    assert response.status_code == 401


# ===== Valid API Key Tests =====

async def test_list_licenses_with_valid_key(
    client: AsyncClient,
    api_key_with_all_permissions: tuple[APIKey, str],
):
    """Valid API key should allow access to list licenses."""
    _, plain_key = api_key_with_all_permissions
    response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 200


async def test_list_customers_with_valid_key(
    client: AsyncClient,
    api_key_with_all_permissions: tuple[APIKey, str],
):
    """Valid API key with can_view_customers should allow listing customers."""
    _, plain_key = api_key_with_all_permissions
    response = await client.get(
        "/api/v1/customers",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 200


async def test_admin_stats_with_valid_key(
    client: AsyncClient,
    api_key_with_all_permissions: tuple[APIKey, str],
):
    """Valid API key should allow access to admin stats."""
    _, plain_key = api_key_with_all_permissions
    response = await client.get(
        "/api/v1/admin/stats",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 200


# ===== Permission Tests =====

async def test_revoke_license_requires_can_revoke_permission(
    client: AsyncClient,
    api_key_issue_only: tuple[APIKey, str],
):
    """API key without can_revoke_licenses should return 403."""
    _, plain_key = api_key_issue_only
    response = await client.request(
        "DELETE",
        "/api/v1/licenses/00000000-0000-0000-0000-000000000001/revoke",
        json={"reason": "test"},
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 403


# ===== Inactive / Expired API Key Tests =====

async def test_inactive_api_key_returns_401(
    client: AsyncClient,
    test_db,
):
    """Inactive API key should be rejected."""
    plain_key = generate_plain_api_key()
    inactive_key = APIKey(
        key_hash=hash_api_key(plain_key),
        name="Inactive Key",
        is_active=False,
        can_issue_licenses=True,
        can_revoke_licenses=True,
        can_view_customers=True,
    )
    test_db.add(inactive_key)
    await test_db.commit()

    response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 401


async def test_expired_api_key_returns_401(
    client: AsyncClient,
    test_db,
):
    """Expired API key should be rejected."""
    from datetime import datetime, timedelta, timezone

    plain_key = generate_plain_api_key()
    expired_key = APIKey(
        key_hash=hash_api_key(plain_key),
        name="Expired Key",
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        can_issue_licenses=True,
        can_revoke_licenses=True,
        can_view_customers=True,
    )
    test_db.add(expired_key)
    await test_db.commit()

    response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 401


# ===== Admin API Key Management Tests =====

async def test_create_api_key_with_admin_secret(client: AsyncClient):
    """Admin can create a new API key using the api_secret_key."""
    response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "New Test Key", "can_issue_licenses": True},
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Key"
    assert "key" in data
    assert data["key"].startswith("aegis_")
    # The key hash should not be in the response
    assert "key_hash" not in data


async def test_create_api_key_invalid_admin_key(client: AsyncClient):
    """Using an invalid admin key should return 401."""
    response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "Should Fail"},
        headers={"X-API-Key": "wrong-admin-key"},
    )
    assert response.status_code == 401


async def test_list_api_keys_with_admin_secret(client: AsyncClient):
    """Admin can list API keys using the api_secret_key."""
    response = await client.get(
        "/api/v1/admin/api-keys",
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_revoke_api_key_with_admin_secret(client: AsyncClient):
    """Admin can revoke an API key using the api_secret_key."""
    # First create a key
    create_response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "Key To Revoke"},
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert create_response.status_code == 201
    key_id = create_response.json()["id"]

    # Revoke it
    revoke_response = await client.delete(
        f"/api/v1/admin/api-keys/{key_id}",
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert revoke_response.status_code == 204

    # Verify it can no longer authenticate
    plain_key = create_response.json()["key"]
    check_response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )
    assert check_response.status_code == 401


async def test_revoke_nonexistent_api_key_returns_404(client: AsyncClient):
    """Revoking a non-existent API key should return 404."""
    response = await client.delete(
        "/api/v1/admin/api-keys/99999",
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert response.status_code == 404


async def test_created_api_key_is_usable(client: AsyncClient):
    """A newly created API key should work for authentication."""
    # Create a new key
    create_response = await client.post(
        "/api/v1/admin/api-keys",
        json={
            "name": "Usable Key",
            "can_issue_licenses": True,
            "can_view_customers": True,
        },
        headers={"X-API-Key": settings.api_secret_key},
    )
    assert create_response.status_code == 201
    plain_key = create_response.json()["key"]

    # Use the new key to access a protected endpoint
    response = await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )
    assert response.status_code == 200


async def test_usage_count_increments(
    client: AsyncClient,
    api_key_with_all_permissions: tuple[APIKey, str],
    test_db,
):
    """API key usage_count should increment on each authenticated request."""
    db_key, plain_key = api_key_with_all_permissions
    initial_count = db_key.usage_count

    await client.get(
        "/api/v1/licenses",
        headers={"X-API-Key": plain_key},
    )

    await test_db.refresh(db_key)
    assert db_key.usage_count == initial_count + 1
