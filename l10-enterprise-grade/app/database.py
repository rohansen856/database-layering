"""Database layer with sharding and circuit breakers"""
import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
import hashlib
from app.config import settings, SHARDS
from app.circuit_breaker import get_circuit_breaker
from app.metrics import db_queries_total, db_query_duration, active_connections, Timer

pools = {}

def init_pools():
    """Initialize all shard pools"""
    for shard_name, shard_url in SHARDS.items():
        pools[shard_name] = ConnectionPool(
            conninfo=shard_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size
        )
        init_schema(shard_name)
    print(f"Initialized {len(pools)} database shards")

def close_pools():
    """Close all shard pools"""
    for pool in pools.values():
        if pool:
            pool.close()

def get_shard_for_key(key: str) -> str:
    """Determine which shard to use for a key"""
    hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
    shard_index = hash_value % len(SHARDS)
    return list(SHARDS.keys())[shard_index]

@contextmanager
def get_connection(shard: str):
    """Get connection with circuit breaker protection"""
    if shard not in pools:
        raise ValueError(f"Shard {shard} not initialized")

    circuit_breaker = get_circuit_breaker(shard)

    def _get_conn():
        with pools[shard].connection() as conn:
            return conn

    try:
        conn = circuit_breaker.call(_get_conn)
        # Update active connections metric
        stats = pools[shard].get_stats()
        active_connections.labels(shard=shard).set(stats['pool_available'])
        yield conn
    except Exception as e:
        print(f"Database connection error for {shard}: {e}")
        raise

def init_schema(shard: str):
    """Initialize schema for a shard"""
    with pools[shard].connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_updated_at
                ON records(updated_at DESC)
            """)
            conn.commit()

def write_record(key: str, value: str) -> str:
    """Write record to appropriate shard"""
    shard = get_shard_for_key(key)

    with Timer() as timer:
        with get_connection(shard) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO records (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP
                """, (key, value))
                conn.commit()

    # Record metrics
    db_queries_total.labels(shard=shard).inc()
    db_query_duration.labels(shard=shard).observe(timer.duration)

    return shard

def read_record(shard: str, key: str) -> str:
    """Read record from specific shard"""
    with Timer() as timer:
        with get_connection(shard) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM records WHERE key = %s", (key,))
                result = cur.fetchone()

    # Record metrics
    db_queries_total.labels(shard=shard).inc()
    db_query_duration.labels(shard=shard).observe(timer.duration)

    return result[0] if result else None

def get_shard_stats(shard: str) -> dict:
    """Get statistics for a shard"""
    if shard in pools:
        return pools[shard].get_stats()
    return {}

def is_shard_healthy(shard: str) -> bool:
    """Check if shard is healthy"""
    try:
        with get_connection(shard) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except:
        return False
