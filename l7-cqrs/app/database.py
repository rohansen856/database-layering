import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from app.config import settings

# Separate pools for write and read databases
write_pool = None
read_pool = None

def init_pools():
    """Initialize connection pools for both databases"""
    global write_pool, read_pool
    
    write_pool = ConnectionPool(
        conninfo=settings.write_db_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        open=True
    )
    
    read_pool = ConnectionPool(
        conninfo=settings.read_db_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        open=True
    )

def close_pools():
    """Close both connection pools"""
    global write_pool, read_pool
    
    if write_pool:
        write_pool.close()
        write_pool = None
    
    if read_pool:
        read_pool.close()
        read_pool = None

def get_write_pool():
    """Get write database pool"""
    return write_pool

def get_read_pool():
    """Get read database pool"""
    return read_pool

@contextmanager
def get_write_connection():
    """Get a connection to the write database"""
    if not write_pool:
        raise ValueError("Write pool not initialized")
    
    with write_pool.connection() as conn:
        yield conn

@contextmanager
def get_read_connection():
    """Get a connection to the read database"""
    if not read_pool:
        raise ValueError("Read pool not initialized")
    
    with read_pool.connection() as conn:
        yield conn

def init_write_db():
    """Initialize write database schema (normalized OLTP)"""
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            # Write-optimized table (normalized)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS commands (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for lookups
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_commands_key 
                ON commands(key)
            """)
            
            conn.commit()

def init_read_db():
    """Initialize read database schema (denormalized OLAP)"""
    with get_read_connection() as conn:
        with conn.cursor() as cur:
            # Read-optimized table (denormalized with aggregates)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    read_count INTEGER DEFAULT 0,
                    write_count INTEGER DEFAULT 0
                )
            """)
            
            # Additional indexes for read performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_updated_at 
                ON records(updated_at DESC)
            """)
            
            conn.commit()
