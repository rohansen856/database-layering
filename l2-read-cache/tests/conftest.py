import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_pool, init_db, close_pool, get_db_connection
from app.cache import init_redis, close_redis, get_redis
import time

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database and cache before all tests"""
    # Wait for services to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            init_pool()
            init_redis()
            init_db()
            break
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(1)

    yield

    # Cleanup after all tests
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS records")
                conn.commit()
    except:
        pass
    finally:
        close_pool()
        close_redis()

@pytest.fixture(autouse=True)
def clean_database_and_cache():
    """Clean database and cache before each test"""
    try:
        # Clean database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE records RESTART IDENTITY")
                conn.commit()

        # Clean cache
        redis_client = get_redis()
        if redis_client:
            redis_client.flushdb()
    except:
        pass
    yield

@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)
