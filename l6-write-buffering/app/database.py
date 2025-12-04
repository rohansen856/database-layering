import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from app.config import settings

pool = None

def init_pool():
    """Initialize connection pool"""
    global pool
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        open=True
    )

def close_pool():
    """Close connection pool"""
    global pool
    if pool:
        pool.close()
        pool = None

def get_pool():
    """Get the connection pool"""
    return pool

@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    if not pool:
        raise ValueError("Pool not initialized")

    with pool.connection() as conn:
        yield conn

def init_db():
    """Initialize database schema"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create records table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on updated_at
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_updated_at
                ON records(updated_at)
            """)

            conn.commit()
