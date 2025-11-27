import pytest
from app.cache import get_from_cache, set_in_cache, invalidate_cache, get_redis

def test_redis_connection():
    """Test that we can connect to Redis"""
    redis_client = get_redis()
    assert redis_client is not None
    assert redis_client.ping()

def test_cache_set_and_get():
    """Test setting and getting values from cache"""
    test_data = {"key": "test", "value": "data", "created_at": "2024-01-01"}

    # Set in cache
    set_in_cache("test", test_data)

    # Get from cache
    cached = get_from_cache("test")
    assert cached is not None
    assert cached["key"] == "test"
    assert cached["value"] == "data"

def test_cache_invalidation():
    """Test cache invalidation"""
    test_data = {"key": "invalidate_test", "value": "data"}

    # Set in cache
    set_in_cache("invalidate_test", test_data)
    assert get_from_cache("invalidate_test") is not None

    # Invalidate
    invalidate_cache("invalidate_test")

    # Should be gone
    assert get_from_cache("invalidate_test") is None

def test_cache_ttl():
    """Test that cache respects TTL"""
    import time

    test_data = {"key": "ttl_test", "value": "data"}

    # Set with 1 second TTL
    set_in_cache("ttl_test", test_data, ttl=1)
    assert get_from_cache("ttl_test") is not None

    # Wait for expiration
    time.sleep(2)

    # Should be expired
    assert get_from_cache("ttl_test") is None

def test_cache_nonexistent_key():
    """Test getting non-existent key from cache"""
    result = get_from_cache("does_not_exist")
    assert result is None

def test_cache_overwrite():
    """Test overwriting existing cache entry"""
    data1 = {"key": "overwrite_test", "value": "first"}
    data2 = {"key": "overwrite_test", "value": "second"}

    set_in_cache("overwrite_test", data1)
    assert get_from_cache("overwrite_test")["value"] == "first"

    set_in_cache("overwrite_test", data2)
    assert get_from_cache("overwrite_test")["value"] == "second"
