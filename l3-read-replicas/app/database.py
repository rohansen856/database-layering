from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from contextlib import contextmanager
from app.config import settings
import psycopg

# Global connection pools
primary_pool = None
replica_pool = None

def init_pools():
    """Initialize connection pools for primary and replica"""
    global primary_pool, replica_pool

    # Primary pool for writes
    primary_pool = ConnectionPool(
        conninfo=settings.primary_database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        open=True
    )

    # Replica pool for reads
    replica_pool = ConnectionPool(
        conninfo=settings.replica_database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        open=True
    )

def close_pools():
    """Close connection pools"""
    global primary_pool, replica_pool
    if primary_pool:
        primary_pool.close()
    if replica_pool:
        replica_pool.close()

def init_db():
    """Initialize database schema on primary"""
    with primary_pool.connection() as conn:
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
def get_primary_connection():
    """Get a connection from the primary pool (for writes)"""
    with primary_pool.connection() as conn:
        yield conn

@contextmanager
def get_replica_connection():
    """Get a connection from the replica pool (for reads)"""
    with replica_pool.connection() as conn:
        yield conn

def get_primary_pool():
    """Get the primary pool instance"""
    return primary_pool

def get_replica_pool():
    """Get the replica pool instance"""
    return replica_pool
