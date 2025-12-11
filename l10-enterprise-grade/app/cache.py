"""Multi-tier cache with L1 (in-process) and L2 (Redis)"""
import redis
from cachetools import TTLCache
from app.config import settings
from app.circuit_breaker import get_circuit_breaker
from app.metrics import cache_hits_total, cache_misses_total

# L1 Cache (in-process)
l1_cache = TTLCache(maxsize=1000, ttl=60)

# L2 Cache (Redis)
l2_cache_client = None

def init_caches():
    """Initialize both cache layers"""
    global l2_cache_client
    l2_cache_client = redis.from_url(settings.cache_l2_url, decode_responses=True)
    l2_cache_client.ping()
    print("Multi-tier cache initialized")

def close_caches():
    """Close cache connections"""
    global l2_cache_client
    if l2_cache_client:
        l2_cache_client.close()

def cache_get(key: str) -> tuple[str, str]:
    """
    Get from cache with L1 -> L2 fallback
    Returns: (value, cache_level) where cache_level is 'L1', 'L2', or None
    """
    cache_key = f"record:{key}"

    # Try L1 first
    if cache_key in l1_cache:
        cache_hits_total.labels(cache_level='L1').inc()
        return (l1_cache[cache_key], 'L1')

    # Try L2
    if l2_cache_client:
        circuit_breaker = get_circuit_breaker('cache_l2')
        try:
            def _get_l2():
                return l2_cache_client.get(cache_key)

            value = circuit_breaker.call(_get_l2)
            if value:
                # Promote to L1
                l1_cache[cache_key] = value
                cache_hits_total.labels(cache_level='L2').inc()
                return (value, 'L2')
        except:
            pass

    # Cache miss
    cache_misses_total.inc()
    return (None, None)

def cache_set(key: str, value: str):
    """Set in both cache layers"""
    cache_key = f"record:{key}"

    # Set in L1
    l1_cache[cache_key] = value

    # Set in L2
    if l2_cache_client:
        try:
            circuit_breaker = get_circuit_breaker('cache_l2')

            def _set_l2():
                l2_cache_client.setex(cache_key, settings.cache_ttl, value)

            circuit_breaker.call(_set_l2)
        except Exception as e:
            print(f"L2 cache set error: {e}")

def cache_delete(key: str):
    """Delete from both cache layers"""
    cache_key = f"record:{key}"

    # Delete from L1
    if cache_key in l1_cache:
        del l1_cache[cache_key]

    # Delete from L2
    if l2_cache_client:
        try:
            l2_cache_client.delete(cache_key)
        except:
            pass

def get_cache_stats() -> dict:
    """Get cache statistics"""
    l2_keys = 0
    if l2_cache_client:
        try:
            l2_keys = l2_cache_client.dbsize()
        except:
            pass

    return {
        "l1_size": len(l1_cache),
        "l1_maxsize": l1_cache.maxsize,
        "l2_keys": l2_keys
    }

def is_cache_healthy(cache_name: str) -> bool:
    """Check if cache is healthy"""
    try:
        if cache_name == "L1":
            return True  # In-process cache always available
        elif cache_name == "L2" and l2_cache_client:
            l2_cache_client.ping()
            return True
    except:
        pass
    return False
