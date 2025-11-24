import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db_connection
import time

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database before all tests"""
    # Wait for database to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
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

@pytest.fixture(autouse=True)
def clean_database():
    """Clean database before each test"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE records RESTART IDENTITY")
                conn.commit()
    except:
        pass
    yield

@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)
