"""Pytest configuration and fixtures for Layer 8 tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.postgres_db import init_pool, close_pool, init_schema
from app.mongodb import init_mongodb, close_mongodb
from app.cache import init_cache, close_cache

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initialize all database systems before tests"""
    print("\n=== Setting up Polyglot Persistence (PostgreSQL + MongoDB + Redis) ===")
    init_pool()
    init_mongodb()
    init_cache()
    init_schema()
    print("=== Setup complete ===\n")

    yield

    print("\n=== Cleaning up ===")
    close_pool()
    close_mongodb()
    close_cache()
    print("=== Cleanup complete ===\n")

@pytest.fixture(scope="session")
def test_client():
    """Create test client for the API"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to ensure isolation"""
    from app.cache import get_cache_client
    try:
        client = get_cache_client()
        if client:
            client.flushdb()  # Clear only the current database
    except:
        pass
    yield
