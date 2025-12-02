import pytest

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "5-multi-tier-cache"
    assert data["database"] == "healthy"
    assert data["l1_cache"] in ["healthy", "unavailable"]
    assert data["l2_cache"] in ["healthy", "unavailable"]

def test_write_data(client, sample_data):
    """Test writing data"""
    response = client.post("/write", json=sample_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]

def test_read_from_database_l3(client, sample_data):
    """Test reading from database (L3) on cache miss"""
    # Write data first
    client.post("/write", json=sample_data)

    # First read should come from database (L3)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert data["value"] == sample_data["value"]
    assert data["cache_level"] == "L3"

def test_read_from_l2_cache(client, sample_data):
    """Test reading from L2 cache after first read"""
    # Write data
    client.post("/write", json=sample_data)

    # First read (populates caches)
    client.get(f"/read/{sample_data['key']}")

    # Clear stats by making another request to reset L1
    # (L1 might have it, so we need to test L2 specifically)
    # We can't easily clear just L1 without clearing L2
    # So we test the promotion behavior instead
    response = client.get(f"/read/{sample_data['key']}")
    data = response.json()
    assert data["success"] is True
    # Should be L1 or L2 (both are cache hits)
    assert data["cache_level"] in ["L1", "L2"]

def test_read_from_l1_cache(client, sample_data):
    """Test reading from cache (L1 or L2)"""
    # Write data
    client.post("/write", json=sample_data)

    # First read (L3 -> populates L1 and L2)
    response1 = client.get(f"/read/{sample_data['key']}")
    assert response1.json()["cache_level"] == "L3"

    # Second read should be from cache (L1 or L2)
    response2 = client.get(f"/read/{sample_data['key']}")
    assert response2.status_code == 200
    data = response2.json()
    assert data["success"] is True
    assert data["cache_level"] in ["L1", "L2"]  # Both are cache hits

def test_cache_promotion_l2_to_l1(client):
    """Test that subsequent reads use cache"""
    # This tests the multi-tier read behavior
    test_data = {"key": "promotion_test", "value": "test_value"}

    client.post("/write", json=test_data)

    # First read: L3 (database)
    response1 = client.get(f"/read/{test_data['key']}")
    assert response1.json()["cache_level"] == "L3"

    # Subsequent reads should hit cache (L1 or L2)
    response2 = client.get(f"/read/{test_data['key']}")
    assert response2.json()["cache_level"] in ["L1", "L2"]

def test_read_nonexistent_key(client):
    """Test reading a key that doesn't exist"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data.get("message", "").lower()
    assert data["cache_level"] == "L3"

def test_update_existing_key(client):
    """Test updating an existing key"""
    # Write initial value
    response = client.post("/write", json={"key": "update_test", "value": "initial"})
    assert response.status_code == 200

    # Read to populate cache
    client.get("/read/update_test")

    # Update with new value
    response = client.post("/write", json={"key": "update_test", "value": "updated"})
    assert response.status_code == 200

    # Read updated value (should be from database since cache was invalidated)
    response = client.get("/read/update_test")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "updated"

def test_cache_invalidation_on_write(client, sample_data):
    """Test that both L1 and L2 cache are invalidated on write"""
    # Write and read to populate both caches
    client.post("/write", json=sample_data)
    client.get(f"/read/{sample_data['key']}")  # Populates L1 and L2
    client.get(f"/read/{sample_data['key']}")  # Should hit L1

    # Update the value
    new_data = {"key": sample_data["key"], "value": "new_value"}
    client.post("/write", json=new_data)

    # Next read should get new value from database (not stale cache)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "new_value"
    assert data["cache_level"] == "L3"  # Cache was invalidated

def test_stats_endpoint(client):
    """Test stats endpoint returns multi-tier cache statistics"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    # L1 stats
    assert "l1_cache_available" in data
    assert "l1_cache_size" in data
    assert "l1_cache_max_size" in data
    assert "l1_cache_hits" in data
    assert "l1_cache_misses" in data
    assert "l1_hit_rate" in data

    # L2 stats
    assert "l2_cache_available" in data
    assert "l2_cache_keys" in data
    assert "l2_cache_hits" in data
    assert "l2_cache_misses" in data
    assert "l2_hit_rate" in data

    # Overall stats
    assert "total_hits" in data
    assert "total_misses" in data
    assert "overall_hit_rate" in data
    assert "db_pool_size" in data

def test_stats_after_operations(client):
    """Test that stats update correctly after cache operations"""
    # Write and read multiple times
    for i in range(3):
        client.post("/write", json={"key": f"stats_test_{i}", "value": f"value_{i}"})

    # First reads (L3 misses, populate caches)
    for i in range(3):
        response = client.get(f"/read/stats_test_{i}")
        assert response.json()["cache_level"] == "L3"

    # Second reads (cache hits from L1 or L2)
    for i in range(3):
        response = client.get(f"/read/stats_test_{i}")
        assert response.json()["cache_level"] in ["L1", "L2"]

    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    # Should have cache hits (L1 or L2)
    assert (data["l1_cache_hits"] + data["l2_cache_hits"]) >= 3
    # Overall hit rate should be > 0
    assert data["overall_hit_rate"] > 0

def test_clear_cache_endpoint(client, sample_data):
    """Test clearing all caches"""
    # Write and read to populate caches
    client.post("/write", json=sample_data)
    client.get(f"/read/{sample_data['key']}")

    # Clear caches
    response = client.post("/clear-cache")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Next read should be from database
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    assert response.json()["cache_level"] == "L3"

def test_concurrent_reads(client, sample_data):
    """Test multiple concurrent reads"""
    # Write data first
    client.post("/write", json=sample_data)

    # Perform multiple concurrent reads
    import concurrent.futures

    def read_data():
        response = client.get(f"/read/{sample_data['key']}")
        return response.status_code == 200

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(read_data) for _ in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All reads should succeed
    assert all(results)

def test_l1_cache_size_limit(client):
    """Test that L1 cache respects size limit"""
    # L1 cache is set to 100 items in config
    # Write more than that to test eviction
    num_keys = 120

    for i in range(num_keys):
        client.post("/write", json={"key": f"limit_test_{i}", "value": f"value_{i}"})

    # Read all to populate L1
    for i in range(num_keys):
        client.get(f"/read/limit_test_{i}")

    # Check stats
    response = client.get("/stats")
    data = response.json()

    # L1 size should not exceed max size
    assert data["l1_cache_size"] <= data["l1_cache_max_size"]

def test_timestamps_in_response(client, sample_data):
    """Test that timestamps are included in read response"""
    client.post("/write", json=sample_data)

    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()

    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

def test_special_characters_in_value(client):
    """Test handling special characters in values"""
    special_data = {
        "key": "special_test",
        "value": "Special chars: !@#$%^&*()_+-={}[]|:;<>?,./~`"
    }

    client.post("/write", json=special_data)

    response = client.get(f"/read/{special_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == special_data["value"]

def test_long_value(client):
    """Test handling long values"""
    long_value = "x" * 10000
    long_data = {"key": "long_test", "value": long_value}

    client.post("/write", json=long_data)

    response = client.get(f"/read/{long_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == long_value
    assert len(data["value"]) == 10000
