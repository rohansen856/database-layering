"""Redis cache layer"""
import redis
import json
from app.config import settings

redis_client = None

def init_cache():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    # Test connection
    redis_client.ping()
    print("Redis cache connected")

def close_cache():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        print("Redis cache closed")

def get_cache_client():
    """Get Redis client"""
    if not redis_client:
        raise ValueError("Redis cache not initialized")
    return redis_client

def cache_set(key: str, value: any, ttl: int = None):
    """Set a value in cache"""
    client = get_cache_client()
    if ttl is None:
        ttl = settings.cache_ttl
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    client.setex(key, ttl, value)

def cache_get(key: str) -> any:
    """Get a value from cache"""
    client = get_cache_client()
    value = client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None

def cache_delete(key: str):
    """Delete a key from cache"""
    client = get_cache_client()
    client.delete(key)

def cache_keys_count() -> int:
    """Get number of keys in cache"""
    client = get_cache_client()
    return client.dbsize()
