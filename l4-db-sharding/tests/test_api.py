import pytest

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "4-db-sharding"
    assert "shards" in data
    assert data["cache"] in ["healthy", "unavailable"]

def test_write_to_shard(client, sample_data):
    """Test writing data is routed to correct shard"""
    response = client.post("/write", json=sample_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert "shard_id" in data
    assert 0 <= data["shard_id"] < 3
    assert f"shard {data['shard_id']}" in data["message"].lower()

def test_read_from_shard_cache_miss(client, sample_data):
    """Test reading from correct shard (cache miss)"""
    # Write data first
    write_response = client.post("/write", json=sample_data)
    write_data = write_response.json()
    shard_id = write_data["shard_id"]

    # Read should come from shard (cache miss)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert data["value"] == sample_data["value"]
    assert data["from_cache"] is False
    assert data["shard_id"] == shard_id

def test_read_from_cache_hit(client, sample_data):
    """Test reading from cache (cache hit)"""
    # Write data first
    client.post("/write", json=sample_data)

    # First read (cache miss, populates cache)
    client.get(f"/read/{sample_data['key']}")

    # Second read should come from cache
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["from_cache"] is True

def test_read_nonexistent_key(client):
    """Test reading a key that doesn't exist"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data.get("message", "").lower()
    assert "shard_id" in data

def test_update_existing_key(client):
    """Test updating an existing key"""
    # Write initial value
    response = client.post("/write", json={"key": "update_test", "value": "initial"})
    assert response.status_code == 200
    initial_shard = response.json()["shard_id"]

    # Update with new value
    response = client.post("/write", json={"key": "update_test", "value": "updated"})
    assert response.status_code == 200
    updated_shard = response.json()["shard_id"]

    # Same key should always go to same shard
    assert initial_shard == updated_shard

    # Read updated value
    response = client.get("/read/update_test")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "updated"
    assert data["shard_id"] == initial_shard

def test_cache_invalidation_on_write(client, sample_data):
    """Test that cache is invalidated when data is written"""
    # Write and read to populate cache
    client.post("/write", json=sample_data)
    client.get(f"/read/{sample_data['key']}")

    # Update the value
    new_data = {"key": sample_data["key"], "value": "new_value"}
    client.post("/write", json=new_data)

    # Next read should get new value (not stale cache)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "new_value"

def test_multiple_writes_to_different_shards(client):
    """Test writing multiple keys that go to different shards"""
    keys = []
    shard_ids = set()

    # Write multiple keys until we hit different shards
    for i in range(20):
        key = f"multi_key_{i}"
        response = client.post("/write", json={"key": key, "value": f"value_{i}"})
        assert response.status_code == 200
        shard_id = response.json()["shard_id"]
        keys.append((key, shard_id))
        shard_ids.add(shard_id)

    # Verify we hit multiple shards (with 20 keys and 3 shards, very likely)
    assert len(shard_ids) > 1

    # Verify all keys can be read back
    for key, expected_shard in keys:
        response = client.get(f"/read/{key}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["shard_id"] == expected_shard

def test_stats_endpoint(client):
    """Test stats endpoint returns shard and cache information"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    assert "cache_available" in data
    assert "num_shards" in data
    assert data["num_shards"] == 3
    assert "shard_pool_sizes" in data
    assert "shard_distribution" in data

    # Check shard pool sizes
    assert "shard_0" in data["shard_pool_sizes"]
    assert "shard_1" in data["shard_pool_sizes"]
    assert "shard_2" in data["shard_pool_sizes"]

def test_shard_distribution_in_stats(client):
    """Test that stats show distribution across shards"""
    # Write keys to various shards
    for i in range(10):
        client.post("/write", json={"key": f"dist_key_{i}", "value": f"value_{i}"})

    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    # Check shard distribution
    distribution = data["shard_distribution"]
    total_records = sum(distribution.values())
    assert total_records == 10

def test_cache_stats_after_operations(client):
    """Test that cache stats update correctly"""
    # Write and read multiple times
    for i in range(5):
        client.post("/write", json={"key": f"stats_test_{i}", "value": f"value_{i}"})

    # First reads (cache misses)
    for i in range(5):
        client.get(f"/read/stats_test_{i}")

    # Second reads (cache hits)
    for i in range(5):
        client.get(f"/read/stats_test_{i}")

    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    if data["cache_available"]:
        assert data["cache_hits"] >= 5
        assert data["cache_misses"] >= 5
        assert data["cache_keys"] >= 5

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
