import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db_connection, init_pool, close_pool, init_db
from app.cache import init_redis, close_redis, redis_client
from app.queue import init_queue, close_queue, dequeue_writes
from app.worker import process_writes

@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """Setup database pool, cache, and queue once for all tests"""
    init_pool()
    init_redis()
    init_queue()
    init_db()

    yield

    close_pool()
    close_redis()
    close_queue()

@pytest.fixture(autouse=True)
def cleanup_data():
    """Clean up test data before each test"""
    yield

    # Process any queued writes before cleaning
    for _ in range(5):  # Process up to 5 batches
        writes = dequeue_writes(batch_size=100)
        if not writes:
            break
        process_writes(writes)

    # Clean database
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM records")
                conn.commit()
    except Exception:
        pass

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

def process_queue():
    """Helper to process queued writes"""
    writes = dequeue_writes(batch_size=100)
    if writes:
        process_writes(writes)
        return len(writes)
    return 0
