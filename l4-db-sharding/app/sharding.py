import hashlib
from app.config import settings

def get_shard_id(key: str) -> int:
    """
    Hash-based sharding strategy.
    Returns the shard ID (0 to NUM_SHARDS-1) for a given key.
    """
    # Use MD5 hash for consistent distribution
    hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
    shard_id = hash_value % settings.num_shards
    return shard_id

def get_shard_stats() -> dict:
    """
    Get distribution of keys across shards.
    """
    from app.database import get_shard_connection
    from psycopg.rows import dict_row

    stats = {}
    for shard_id in range(settings.num_shards):
        try:
            with get_shard_connection(shard_id) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT COUNT(*) as count FROM records")
                    result = cur.fetchone()
                    stats[f"shard_{shard_id}"] = result['count'] if result else 0
        except Exception:
            stats[f"shard_{shard_id}"] = 0

    return stats
