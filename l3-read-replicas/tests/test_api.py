import pytest
import time
from fastapi.testclient import TestClient

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "3-read-replicas"
    assert data["primary"] == "healthy"
    assert data["replica"] == "healthy"
    assert data["cache"] in ["healthy", "unavailable"]

def test_write_to_primary(client, sample_data):
    """Test writing data to primary database"""
    response = client.post("/write", json=sample_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert "primary" in data["message"].lower()

def test_read_from_replica_cache_miss(client, sample_data):
    """Test reading from replica (cache miss scenario)"""
    # Write data first
    client.post("/write", json=sample_data)

    # Wait for replication
    time.sleep(1)

    # First read should come from replica (cache miss)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert data["value"] == sample_data["value"]
    assert data["from_cache"] is False
    assert data["from_replica"] is True

def test_read_from_cache_hit(client, sample_data):
    """Test reading from cache (cache hit scenario)"""
    # Write data first
    client.post("/write", json=sample_data)

    # Wait for replication
    time.sleep(1)

    # First read (cache miss, populates cache)
    client.get(f"/read/{sample_data['key']}")

    # Second read should come from cache
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["from_cache"] is True
    assert data["from_replica"] is False

def test_read_nonexistent_key(client):
    """Test reading a key that doesn't exist"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data.get("message", "").lower()

def test_update_existing_key(client):
    """Test updating an existing key"""
    # Write initial value
    response = client.post("/write", json={"key": "update_test", "value": "initial"})
    assert response.status_code == 200

    # Wait for replication
    time.sleep(1)

    # Update with new value
    response = client.post("/write", json={"key": "update_test", "value": "updated"})
    assert response.status_code == 200

    # Wait for replication
    time.sleep(1)

    # Read updated value (should invalidate cache and read from replica)
    response = client.get("/read/update_test")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "updated"

def test_cache_invalidation_on_write(client, sample_data):
    """Test that cache is invalidated when data is written"""
    # Write and read to populate cache
    client.post("/write", json=sample_data)
    time.sleep(1)
    client.get(f"/read/{sample_data['key']}")

    # Update the value
    new_data = {"key": sample_data["key"], "value": "new_value"}
    client.post("/write", json=new_data)
    time.sleep(1)

    # Next read should get new value from replica (not stale cache)
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "new_value"

def test_multiple_writes(client):
    """Test writing multiple different keys"""
    keys = ["key1", "key2", "key3"]

    for key in keys:
        response = client.post("/write", json={"key": key, "value": f"value_{key}"})
        assert response.status_code == 200

    # Wait for replication
    time.sleep(1)

    for key in keys:
        response = client.get(f"/read/{key}")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == f"value_{key}"

def test_stats_endpoint(client, sample_data):
    """Test stats endpoint returns cache and pool information"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    assert "cache_available" in data
    assert "primary_pool_size" in data
    assert "replica_pool_size" in data

    # If cache is available, check cache stats
    if data["cache_available"]:
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "cache_keys" in data
        assert "cache_hit_rate" in data

def test_cache_stats_after_operations(client):
    """Test that cache stats update correctly"""
    # Write and read multiple times
    for i in range(5):
        client.post("/write", json={"key": f"stats_test_{i}", "value": f"value_{i}"})

    time.sleep(1)

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
        assert data["cache_hits"] >= 5  # At least 5 hits from second reads
        assert data["cache_misses"] >= 5  # At least 5 misses from first reads
        assert data["cache_keys"] >= 5  # At least 5 keys stored

def test_concurrent_reads(client, sample_data):
    """Test multiple concurrent reads"""
    # Write data first
    client.post("/write", json=sample_data)
    time.sleep(1)

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
    time.sleep(1)

    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()

    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

def test_write_and_immediate_read(client):
    """Test writing and immediately reading (tests replication lag)"""
    test_data = {"key": "immediate_test", "value": "immediate_value"}

    # Write data
    write_response = client.post("/write", json=test_data)
    assert write_response.status_code == 200

    # Small delay for replication
    time.sleep(1)

    # Read should eventually return the data
    response = client.get(f"/read/{test_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["value"] == test_data["value"]

def test_special_characters_in_value(client):
    """Test handling special characters in values"""
    special_data = {
        "key": "special_test",
        "value": "Special chars: !@#$%^&*()_+-={}[]|:;<>?,./~`"
    }

    client.post("/write", json=special_data)
    time.sleep(1)

    response = client.get(f"/read/{special_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == special_data["value"]

def test_long_value(client):
    """Test handling long values"""
    long_value = "x" * 10000
    long_data = {"key": "long_test", "value": long_value}

    client.post("/write", json=long_data)
    time.sleep(1)

    response = client.get(f"/read/{long_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == long_value
    assert len(data["value"]) == 10000
