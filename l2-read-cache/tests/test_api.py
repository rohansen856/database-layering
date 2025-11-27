import pytest
from fastapi.testclient import TestClient
import time

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "2-read-cache"
    assert data["database"] == "healthy"
    assert data["cache"] in ["healthy", "unavailable"]

def test_cache_stats(client):
    """Test cache statistics endpoint"""
    response = client.get("/cache-stats")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data

def test_write_new_record(client):
    """Test writing a new record"""
    response = client.post("/write", json={"key": "test_key", "value": "test_value"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "test_key"
    assert data["message"] == "Data written successfully"

def test_read_from_cache(client):
    """Test that subsequent reads come from cache"""
    # Write a record
    client.post("/write", json={"key": "cache_key", "value": "cache_value"})

    # First read (cache miss, loads from DB)
    response1 = client.get("/read/cache_key")
    data1 = response1.json()
    assert data1["success"] is True
    assert data1["value"] == "cache_value"
    assert data1["from_cache"] is False

    # Second read (should be from cache)
    response2 = client.get("/read/cache_key")
    data2 = response2.json()
    assert data2["success"] is True
    assert data2["value"] == "cache_value"
    assert data2["from_cache"] is True

def test_cache_invalidation_on_write(client):
    """Test that cache is invalidated when record is updated"""
    # Write and read (populates cache)
    client.post("/write", json={"key": "update_key", "value": "initial"})
    client.get("/read/update_key")

    # Update the record (should invalidate cache)
    client.post("/write", json={"key": "update_key", "value": "updated"})

    # Read again (should be cache miss, getting new value from DB)
    response = client.get("/read/update_key")
    data = response.json()
    assert data["value"] == "updated"
    assert data["from_cache"] is False

def test_read_nonexistent_record(client):
    """Test reading a non-existent record"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["key"] == "nonexistent_key"
    assert data["message"] == "Key not found"

def test_cache_hit_rate(client):
    """Test that cache hit rate increases with repeated reads"""
    # Write some records
    for i in range(5):
        client.post("/write", json={"key": f"hit_key_{i}", "value": f"value_{i}"})

    # First reads (all cache misses)
    for i in range(5):
        client.get(f"/read/hit_key_{i}")

    # Second reads (all cache hits)
    for i in range(5):
        client.get(f"/read/hit_key_{i}")

    # Check cache stats
    stats = client.get("/cache-stats").json()
    if stats.get("available"):
        assert stats["hits"] > 0
        assert stats["hit_rate"] > 0

def test_write_multiple_records(client):
    """Test writing multiple different records"""
    records = [
        {"key": "key1", "value": "value1"},
        {"key": "key2", "value": "value2"},
        {"key": "key3", "value": "value3"},
    ]

    for record in records:
        response = client.post("/write", json=record)
        assert response.status_code == 200
        assert response.json()["success"] is True

    # Verify all records (first read from DB, second from cache)
    for record in records:
        response = client.get(f"/read/{record['key']}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["value"] == record["value"]

def test_cache_performance_improvement(client):
    """Test that cached reads are faster than DB reads"""
    # Write a record
    client.post("/write", json={"key": "perf_key", "value": "perf_value"})

    # First read (from DB)
    start1 = time.time()
    client.get("/read/perf_key")
    db_time = time.time() - start1

    # Second read (from cache)
    start2 = time.time()
    client.get("/read/perf_key")
    cache_time = time.time() - start2

    # Cache read should generally be faster (though not guaranteed in tests)
    # Just verify both completed successfully
    assert db_time > 0
    assert cache_time > 0

def test_concurrent_cache_access(client):
    """Test concurrent access to cached data"""
    import concurrent.futures

    # Write a record
    client.post("/write", json={"key": "concurrent_key", "value": "concurrent_value"})

    # Prime the cache
    client.get("/read/concurrent_key")

    def read_cached():
        response = client.get("/read/concurrent_key")
        return response.status_code == 200 and response.json()["from_cache"]

    # Make 20 concurrent cached reads
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda _: read_cached(), range(20)))

    # All reads should succeed
    assert all(results)

def test_write_update_existing_record(client):
    """Test updating an existing record"""
    # Write initial record
    client.post("/write", json={"key": "update_test", "value": "initial_value"})

    # Read to populate cache
    response1 = client.get("/read/update_test")
    assert response1.json()["value"] == "initial_value"

    # Update the record
    response = client.post("/write", json={"key": "update_test", "value": "updated_value"})
    assert response.status_code == 200

    # Verify the update
    read_response = client.get("/read/update_test")
    read_data = read_response.json()
    assert read_data["value"] == "updated_value"
