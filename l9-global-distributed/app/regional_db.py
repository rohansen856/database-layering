"""Regional database management"""
import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from app.config import settings, REGIONS
import redis

# Regional database pools
pools = {}

# Regional cache clients
caches = {}

def init_all_regions():
    """Initialize connections for all regions"""
    for region_key, region_config in REGIONS.items():
        init_region(region_key)
    print("All regions initialized")

def init_region(region: str):
    """Initialize a specific region's database and cache"""
    global pools, caches

    region_config = REGIONS[region]

    # Initialize database pool
    pools[region] = ConnectionPool(
        conninfo=region_config["db_url"],
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size
    )

    # Initialize cache
    caches[region] = redis.from_url(region_config["cache_url"], decode_responses=True)

    # Initialize schema
    init_schema(region)

    print(f"Region {region_config['name']} initialized")

def close_all_regions():
    """Close all regional connections"""
    for region, pool in pools.items():
        if pool:
            pool.close()
    for region, cache in caches.items():
        if cache:
            cache.close()
    print("All regions closed")

@contextmanager
def get_connection(region: str):
    """Get a database connection for a specific region"""
    if region not in pools:
        raise ValueError(f"Region {region} not initialized")
    with pools[region].connection() as conn:
        yield conn

def get_cache(region: str):
    """Get cache client for a specific region"""
    if region not in caches:
        raise ValueError(f"Region {region} cache not initialized")
    return caches[region]

def init_schema(region: str):
    """Initialize database schema for a region"""
    with get_connection(region) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    region VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_region ON records(region)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_updated_at ON records(updated_at DESC)
            """)
            conn.commit()

def write_record(region: str, key: str, value: str) -> bool:
    """Write a record to a specific region"""
    with get_connection(region) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (key, value, region, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, region))
            conn.commit()

    # Invalidate cache
    cache = get_cache(region)
    cache.delete(f"record:{key}")

    return True

def read_record(region: str, key: str) -> tuple:
    """Read a record from a specific region
    Returns: (value, source) where source is 'cache' or 'database'
    """
    # Try cache first
    cache = get_cache(region)
    cache_key = f"record:{key}"
    cached_value = cache.get(cache_key)

    if cached_value:
        return (cached_value, "cache")

    # Try database
    with get_connection(region) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM records WHERE key = %s", (key,))
            result = cur.fetchone()

    if result:
        value = result[0]
        # Cache the result
        cache.setex(cache_key, settings.cache_ttl, value)
        return (value, "database")

    return (None, "database")

def get_record_count(region: str) -> int:
    """Get total records in a region"""
    with get_connection(region) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM records")
            return cur.fetchone()[0]

def get_cache_keys_count(region: str) -> int:
    """Get number of keys in regional cache"""
    cache = get_cache(region)
    return cache.dbsize()

def get_pool_stats(region: str) -> dict:
    """Get pool statistics for a region"""
    if region in pools:
        return pools[region].get_stats()
    return {}

def is_region_healthy(region: str) -> bool:
    """Check if a region is healthy"""
    try:
        cache = get_cache(region)
        cache.ping()
        with get_connection(region) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except:
        return False
