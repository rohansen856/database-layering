import redis
import json
from cachetools import TTLCache
from app.config import settings
import threading

# L1 Cache: In-process TTL cache (thread-safe)
l1_cache = None
l1_lock = threading.RLock()
l1_hits = 0
l1_misses = 0

# L2 Cache: Redis
redis_client = None
l2_hits = 0
l2_misses = 0

def init_caches():
    """Initialize both L1 and L2 caches"""
    global l1_cache, redis_client

    # Initialize L1 cache (in-process)
    l1_cache = TTLCache(maxsize=settings.l1_cache_size, ttl=settings.l1_cache_ttl)
    print(f"L1 cache initialized: max_size={settings.l1_cache_size}, ttl={settings.l1_cache_ttl}s")

    # Initialize L2 cache (Redis)
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        redis_client.ping()
        print("L2 cache (Redis) connected successfully")
    except Exception as e:
        print(f"L2 cache (Redis) connection failed: {e}")
        redis_client = None

def close_caches():
    """Close cache connections"""
    global l1_cache, redis_client

    if l1_cache:
        l1_cache.clear()
        l1_cache = None

    if redis_client:
        redis_client.close()
        redis_client = None

def get_from_l1(key: str):
    """Get data from L1 cache"""
    global l1_hits, l1_misses

    if not l1_cache:
        l1_misses += 1
        return None

    try:
        with l1_lock:
            if key in l1_cache:
                l1_hits += 1
                return l1_cache[key]
            else:
                l1_misses += 1
                return None
    except Exception as e:
        print(f"L1 cache get error: {e}")
        l1_misses += 1
        return None

def set_in_l1(key: str, value: dict):
    """Set data in L1 cache"""
    if not l1_cache:
        return

    try:
        with l1_lock:
            l1_cache[key] = value
    except Exception as e:
        print(f"L1 cache set error: {e}")

def invalidate_l1(key: str):
    """Invalidate L1 cache entry"""
    if not l1_cache:
        return

    try:
        with l1_lock:
            if key in l1_cache:
                del l1_cache[key]
    except Exception as e:
        print(f"L1 cache invalidation error: {e}")

def get_from_l2(key: str):
    """Get data from L2 cache (Redis)"""
    global l2_hits, l2_misses

    if not redis_client:
        l2_misses += 1
        return None

    try:
        cached_data = redis_client.get(f"record:{key}")
        if cached_data:
            l2_hits += 1
            return json.loads(cached_data)
        else:
            l2_misses += 1
            return None
    except Exception as e:
        print(f"L2 cache get error: {e}")
        l2_misses += 1
        return None

def set_in_l2(key: str, value: dict):
    """Set data in L2 cache (Redis)"""
    if not redis_client:
        return

    try:
        redis_client.setex(
            f"record:{key}",
            settings.l2_cache_ttl,
            json.dumps(value, default=str)
        )
    except Exception as e:
        print(f"L2 cache set error: {e}")

def invalidate_l2(key: str):
    """Invalidate L2 cache entry"""
    if not redis_client:
        return

    try:
        redis_client.delete(f"record:{key}")
    except Exception as e:
        print(f"L2 cache invalidation error: {e}")

def get_from_cache(key: str):
    """
    Multi-tier cache lookup:
    1. Check L1 (in-process) - fastest
    2. Check L2 (Redis) - fast
    3. Return None if both miss
    """
    # Try L1 first
    data = get_from_l1(key)
    if data:
        return data, "L1"

    # Try L2 next
    data = get_from_l2(key)
    if data:
        # Promote to L1 for future hits
        set_in_l1(key, data)
        return data, "L2"

    return None, None

def set_in_cache(key: str, value: dict):
    """Set data in both L1 and L2 caches"""
    set_in_l1(key, value)
    set_in_l2(key, value)

def invalidate_cache(key: str):
    """Invalidate cache entry from both L1 and L2"""
    invalidate_l1(key)
    invalidate_l2(key)

def clear_all_caches():
    """Clear all cache data"""
    global l1_cache

    # Clear L1
    if l1_cache:
        with l1_lock:
            l1_cache.clear()

    # Clear L2
    if redis_client:
        try:
            redis_client.flushdb()
        except Exception:
            pass

def get_cache_stats():
    """Get combined cache statistics"""
    global l1_hits, l1_misses, l2_hits, l2_misses

    stats = {
        "l1_available": l1_cache is not None,
        "l1_hits": l1_hits,
        "l1_misses": l1_misses,
        "l1_size": len(l1_cache) if l1_cache else 0,
        "l1_max_size": settings.l1_cache_size,
        "l2_available": redis_client is not None,
        "l2_hits": l2_hits,
        "l2_misses": l2_misses,
    }

    if redis_client:
        try:
            keys = redis_client.keys("record:*")
            stats["l2_keys"] = len(keys)
        except Exception:
            stats["l2_keys"] = 0

    return stats
