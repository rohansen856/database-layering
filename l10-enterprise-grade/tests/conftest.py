"""Pytest configuration for Layer 10"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_pools, close_pools
from app.cache import init_caches, close_caches
from app.rate_limiter import init_rate_limiter, close_rate_limiter

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initialize all systems"""
    print("\n=== Setting up Enterprise-Grade System ===")
    init_pools()
    init_caches()
    init_rate_limiter()
    print("=== Setup complete ===\n")

    yield

    print("\n=== Cleaning up ===")
    close_pools()
    close_caches()
    close_rate_limiter()
    print("=== Cleanup complete ===\n")

@pytest.fixture(scope="session")
def test_client():
    """Create test client"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def api_headers():
    """Default API headers with authentication"""
    return {"X-API-Key": "enterprise-api-key-demo", "X-Client-ID": "test-client"}

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limits before each test"""
    from app.rate_limiter import rate_limiter_client
    if rate_limiter_client:
        try:
            # Clear all rate limit keys
            rate_limiter_client.flushdb()
        except:
            pass
    yield
