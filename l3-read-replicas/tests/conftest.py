import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_primary_connection, get_replica_connection, init_pools, close_pools, init_db
from app.cache import init_redis, close_redis, redis_client

@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """Setup database pools and Redis once for all tests"""
    init_pools()
    init_redis()

    # Wait for replica to sync
    time.sleep(2)
    init_db()

    yield

    close_pools()
    close_redis()

@pytest.fixture(autouse=True)
def cleanup_data():
    """Clean up test data before each test"""
    yield

    # Clean primary database
    try:
        with get_primary_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM records")
                conn.commit()
    except Exception:
        pass

    # Wait for replica to sync the delete
    time.sleep(0.5)

    # Clean Redis cache
    try:
        if redis_client:
            redis_client.flushdb()
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
