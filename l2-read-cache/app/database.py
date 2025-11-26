from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from contextlib import contextmanager
from app.config import settings
import psycopg

# Global connection pool
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

def init_db():
    """Initialize database schema"""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_key ON records(key)
            """)
            conn.commit()

@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    with pool.connection() as conn:
        yield conn

def get_pool():
    """Get the connection pool instance"""
    return pool
