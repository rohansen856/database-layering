"""Pytest configuration and fixtures for Layer 7 tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_pools, close_pools, init_write_db, init_read_db
from app.events import init_event_store, close_event_store

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initialize databases and event store before all tests"""
    print("\n=== Setting up databases and event store ===")
    init_pools()
    init_event_store()
    init_write_db()
    init_read_db()
    print("=== Setup complete ===\n")

    yield

    print("\n=== Cleaning up ===")
    close_pools()
    close_event_store()
    print("=== Cleanup complete ===\n")

@pytest.fixture(scope="session")
def test_client():
    """Create test client for the API"""
    with TestClient(app) as client:
        yield client
