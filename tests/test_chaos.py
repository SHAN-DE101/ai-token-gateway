import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.rate_limiter import AtomicRateLimiter
from app.services.circuit_breaker import ProviderCircuitBreaker

client = TestClient(app)

def test_redis_failure_fail_closed_mode(monkeypatch):
    """Verify that when Redis is dead and REDIS_RESILIENCE_MODE=fail_closed, traffic is blocked."""
    monkeypatch.setattr(settings, "REDIS_RESILIENCE_MODE", "fail_closed")
    limiter = AtomicRateLimiter(redis_client=None)  # Simulated broken Redis connection
    
    import asyncio
    allowed, reason, _, _ = asyncio.run(
        limiter.check_and_commit("sk-gw-tenant-prod-001", 1000, 500000, 50)
    )
    assert not allowed
    assert "REDIS_FAIL_CLOSED" in reason

def test_redis_failure_fail_open_mode(monkeypatch):
    """Verify that when Redis is dead and REDIS_RESILIENCE_MODE=fail_open, traffic passes with warning."""
    monkeypatch.setattr(settings, "REDIS_RESILIENCE_MODE", "fail_open")
    limiter = AtomicRateLimiter(redis_client=None)
    
    import asyncio
    allowed, reason, _, _ = asyncio.run(
        limiter.check_and_commit("sk-gw-tenant-prod-001", 1000, 500000, 50)
    )
    assert allowed
    assert reason == "FAIL_OPEN"

def test_provider_circuit_breaker_tripping():
    """Verify provider circuit breaker trips to OPEN after reaching failure threshold."""
    cb = ProviderCircuitBreaker(error_threshold=0.30, window_sec=30.0)
    assert cb.state == "closed"

    # Inject 5 consecutive provider failures
    for _ in range(5):
        cb.record_result(is_success=False)

    assert cb.state == "open"
    assert not cb.can_execute()  # Should fast-fail without forwarding
