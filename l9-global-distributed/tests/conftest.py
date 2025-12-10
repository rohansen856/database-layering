"""Pytest configuration and fixtures for Layer 9 tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.regional_db import init_all_regions, close_all_regions

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initialize all regional databases before tests"""
    print("\n=== Setting up Global Distributed DB (3 regions) ===")
    init_all_regions()
    print("=== Setup complete ===\n")

    yield

    print("\n=== Cleaning up ===")
    close_all_regions()
    print("=== Cleanup complete ===\n")

@pytest.fixture(scope="session")
def test_client():
    """Create test client for the API"""
    with TestClient(app) as client:
        yield client
