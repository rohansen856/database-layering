import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db_connection, init_pool, close_pool, init_db
from app.cache import init_caches, close_caches, clear_all_caches

@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """Setup database pool and caches once for all tests"""
    init_pool()
    init_caches()
    init_db()

    yield

    close_pool()
    close_caches()

@pytest.fixture(autouse=True)
def cleanup_data():
    """Clean up test data before each test"""
    yield

    # Clean database
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM records")
                conn.commit()
    except Exception:
        pass

    # Clean all caches
    try:
        clear_all_caches()
    except Exception:
        pass

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

@pytest.fixture
def sample_data():
    """Sample test data"""
    return {
        "key": "test_key",
        "value": "test_value"
    }
