import redis
import json
from app.config import settings

redis_client = None
cache_hits = 0
cache_misses = 0

def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        redis_client.ping()
        print("Redis connected successfully")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        redis_client = None

def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None

def get_from_cache(key: str):
    """Get data from cache"""
    global cache_hits, cache_misses

    if not redis_client:
        cache_misses += 1
        return None

    try:
        cached_data = redis_client.get(f"record:{key}")
        if cached_data:
            cache_hits += 1
            return json.loads(cached_data)
        else:
            cache_misses += 1
            return None
    except Exception as e:
        print(f"Cache get error: {e}")
        cache_misses += 1
        return None

def set_in_cache(key: str, value: dict, ttl: int = None):
    """Set data in cache with TTL"""
    if not redis_client:
        return

    try:
        cache_ttl = ttl if ttl else settings.cache_ttl
        redis_client.setex(
            f"record:{key}",
            cache_ttl,
            json.dumps(value, default=str)
        )
    except Exception as e:
        print(f"Cache set error: {e}")

def invalidate_cache(key: str):
    """Invalidate cache for a specific key"""
    if not redis_client:
        return

    try:
        redis_client.delete(f"record:{key}")
    except Exception as e:
        print(f"Cache invalidation error: {e}")

def get_cache_stats():
    """Get cache statistics"""
    global cache_hits, cache_misses

    stats = {
        "available": redis_client is not None,
        "hits": cache_hits,
        "misses": cache_misses
    }

    if redis_client:
        try:
            # Get number of keys matching our pattern
            keys = redis_client.keys("record:*")
            stats["keys"] = len(keys)
        except Exception:
            stats["keys"] = 0

    return stats
