import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from app.config import settings

# Connection pools for each shard
shard_pools = {}

def init_shard_pools():
    """Initialize connection pools for all shards"""
    global shard_pools

    shard_urls = [
        settings.shard_0_url,
        settings.shard_1_url,
        settings.shard_2_url
    ]

    for shard_id, shard_url in enumerate(shard_urls):
        shard_pools[shard_id] = ConnectionPool(
            conninfo=shard_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            open=True
        )

def close_shard_pools():
    """Close all shard connection pools"""
    for pool in shard_pools.values():
        if pool:
            pool.close()

def get_shard_pool(shard_id: int):
    """Get the pool for a specific shard"""
    return shard_pools.get(shard_id)

@contextmanager
def get_shard_connection(shard_id: int):
    """Get a connection for a specific shard"""
    pool = shard_pools.get(shard_id)
    if not pool:
        raise ValueError(f"Shard {shard_id} not initialized")

    with pool.connection() as conn:
        yield conn

def init_db():
    """Initialize database schema in all shards"""
    for shard_id in range(settings.num_shards):
        with get_shard_connection(shard_id) as conn:
            with conn.cursor() as cur:
                # Create records table in each shard
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
