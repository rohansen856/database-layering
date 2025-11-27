import redis
import json
from app.config import settings

# Global Redis client
redis_client = None

def init_redis():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        redis_client.close()

def get_redis():
    """Get Redis client instance"""
    return redis_client

def get_from_cache(key: str):
    """Get value from cache"""
    if redis_client is None:
        return None

    try:
        cached = redis_client.get(f"record:{key}")
        if cached:
            return json.loads(cached)
        return None
    except Exception:
        return None

def set_in_cache(key: str, value: dict, ttl: int = None):
    """Set value in cache with TTL"""
    if redis_client is None:
        return

    try:
        ttl = ttl or settings.cache_ttl
        redis_client.setex(
            f"record:{key}",
            ttl,
            json.dumps(value, default=str)
        )
    except Exception:
        pass

def invalidate_cache(key: str):
    """Invalidate cache for a key"""
    if redis_client is None:
        return

    try:
        redis_client.delete(f"record:{key}")
    except Exception:
        pass

def get_cache_stats():
    """Get cache statistics"""
    if redis_client is None:
        return {"available": False}

    try:
        info = redis_client.info("stats")
        return {
            "available": True,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "keys": redis_client.dbsize()
        }
    except Exception:
        return {"available": False}
