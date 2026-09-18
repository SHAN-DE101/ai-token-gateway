import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_virtual_key, VIRTUAL_KEY_REGISTRY

client = TestClient(app)

def test_cross_tenant_key_isolation():
    """Verify tenant A and tenant B have isolated quotas and identities."""
    # Tenant A: org-core-ai (Key: sk-gw-tenant-prod-001)
    # Tenant B: org-finance (Key: sk-gw-tenant-alpha-001)

    res_a = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-prod-001"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Tenant A query"}]}
    )
    assert res_a.status_code == 200

    res_b = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-alpha-001"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Tenant B query"}]}
    )
    assert res_b.status_code == 200

    # Verify model tier boundary: Tenant B is restricted from Claude 3.5 Sonnet
    res_b_restricted = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-alpha-001"},
        json={"model": "claude-3-5-sonnet", "messages": [{"role": "user", "content": "Restricted call"}]}
    )
    assert res_b_restricted.status_code == 403
    assert "not authorized for model tier" in res_b_restricted.json()["detail"]["error"]

    # Verify Tenant A CAN access Claude 3.5 Sonnet (no permission bleed)
    res_a_allowed = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-prod-001"},
        json={"model": "claude-3-5-sonnet", "messages": [{"role": "user", "content": "Allowed call"}]}
    )
    assert res_a_allowed.status_code == 200

def test_revoked_tenant_cannot_poison_active_tenant():
    """Verify a revoked tenant does not impact other active tenant routing."""
    res_revoked = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-revoked-999"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Blocked"}]}
    )
    assert res_revoked.status_code == 403

    # Active tenant must succeed unimpeded
    res_active = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-prod-001"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Valid"}]}
    )
    assert res_active.status_code == 200
