import pytest
import time

def test_health(test_client):
    """Test health endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "9-global-distributed"
    assert data["total_regions"] == 3
    assert data["healthy_regions"] >= 3

def test_list_regions(test_client):
    """Test listing all regions"""
    response = test_client.get("/regions")
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert len(data["regions"]) == 3

    region_names = [r["name"] for r in data["regions"]]
    assert "US-EAST" in region_names
    assert "EU-WEST" in region_names
    assert "ASIA-PAC" in region_names

def test_write_to_us_east(test_client):
    """Test writing data to US-EAST region"""
    response = test_client.post("/write", json={
        "key": "test_us_key",
        "value": "us_value",
        "region": "us-east"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "test_us_key"
    assert data["primary_region"] == "US-EAST"
    assert len(data["replicated_to"]) == 2  # Replicated to other 2 regions

def test_write_to_eu_west(test_client):
    """Test writing data to EU-WEST region"""
    response = test_client.post("/write", json={
        "key": "test_eu_key",
        "value": "eu_value",
        "region": "eu-west"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["primary_region"] == "EU-WEST"

def test_write_to_asia_pac(test_client):
    """Test writing data to ASIA-PAC region"""
    response = test_client.post("/write", json={
        "key": "test_asia_key",
        "value": "asia_value",
        "region": "asia-pac"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["primary_region"] == "ASIA-PAC"

def test_read_from_primary_region(test_client):
    """Test reading from the primary region where data was written"""
    # Write to US-EAST
    test_client.post("/write", json={
        "key": "read_test_key",
        "value": "read_test_value",
        "region": "us-east"
    })

    # Read from US-EAST
    response = test_client.get("/read/read_test_key", headers={"X-Region": "us-east"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["value"] == "read_test_value"
    assert "US-EAST" in data["region"]

def test_global_replication(test_client):
    """Test that data is replicated across all regions"""
    key = "replication_test"
    value = "replicated_value"

    # Write to US-EAST
    write_response = test_client.post("/write", json={
        "key": key,
        "value": value,
        "region": "us-east"
    })
    assert write_response.json()["replicated_to"] == ["EU-WEST", "ASIA-PAC"]

    # Small delay for replication
    time.sleep(0.5)

    # Verify data exists in all regions
    for region in ["us-east", "eu-west", "asia-pac"]:
        response = test_client.get(f"/read/{key}", headers={"X-Region": region})
        assert response.status_code == 200
        assert response.json()["value"] == value

def test_cache_behavior(test_client):
    """Test cache behavior in regional reads"""
    key = "cache_test"
    value = "cache_value"

    # Write data
    test_client.post("/write", json={"key": key, "value": value, "region": "us-east"})

    # First read - from database
    response1 = test_client.get(f"/read/{key}", headers={"X-Region": "us-east"})
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["source"] == "database"

    # Second read - from cache
    response2 = test_client.get(f"/read/{key}", headers={"X-Region": "us-east"})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["source"] == "cache"

def test_read_latency_tracking(test_client):
    """Test that read latency is tracked"""
    test_client.post("/write", json={"key": "latency_test", "value": "value"})

    response = test_client.get("/read/latency_test")
    assert response.status_code == 200
    data = response.json()
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], (int, float))
    assert data["latency_ms"] >= 0

def test_read_nonexistent_key(test_client):
    """Test reading a key that doesn't exist in any region"""
    response = test_client.get("/read/nonexistent_key_12345")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["message"].lower()

def test_regional_failover(test_client):
    """Test that reads fail over to other regions if primary is unavailable"""
    key = "failover_test"
    value = "failover_value"

    # Write to EU-WEST (will replicate to all)
    test_client.post("/write", json={"key": key, "value": value, "region": "eu-west"})
    time.sleep(0.5)

    # Read from different region - should work due to replication
    response = test_client.get(f"/read/{key}", headers={"X-Region": "asia-pac"})
    assert response.status_code == 200
    assert response.json()["value"] == value

def test_stats_endpoint(test_client):
    """Test global statistics endpoint"""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    assert "regions" in data
    assert len(data["regions"]) == 3
    assert data["total_regions"] == 3
    assert data["healthy_regions"] >= 3
    assert "total_records_global" in data
    assert data["replication_enabled"] is True

    # Check each region has stats
    for region_stat in data["regions"]:
        assert "region" in region_stat
        assert "db_pool_size" in region_stat
        assert "cache_keys" in region_stat
        assert "total_records" in region_stat
        assert "healthy" in region_stat

def test_write_with_header(test_client):
    """Test writing with X-Region header"""
    response = test_client.post(
        "/write",
        json={"key": "header_test", "value": "header_value"},
        headers={"X-Region": "eu-west"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["primary_region"] == "EU-WEST"

def test_concurrent_writes_different_regions(test_client):
    """Test concurrent writes to different regions"""
    keys = []
    for i in range(5):
        key = f"concurrent_{i}"
        region = ["us-east", "eu-west", "asia-pac"][i % 3]
        response = test_client.post("/write", json={
            "key": key,
            "value": f"value_{i}",
            "region": region
        })
        assert response.status_code == 200
        keys.append(key)

    # Verify all writes succeeded
    time.sleep(1)
    for key in keys:
        response = test_client.get(f"/read/{key}")
        assert response.status_code == 200
        assert response.json()["success"] is True

def test_data_consistency_across_regions(test_client):
    """Test that replicated data is consistent across regions"""
    key = "consistency_test"
    value = "consistent_value"

    # Write to US-EAST
    test_client.post("/write", json={"key": key, "value": value, "region": "us-east"})
    time.sleep(1)

    # Read from all regions
    values = []
    for region in ["us-east", "eu-west", "asia-pac"]:
        response = test_client.get(f"/read/{key}", headers={"X-Region": region})
        if response.json()["success"]:
            values.append(response.json()["value"])

    # All values should be the same
    assert len(set(values)) == 1
    assert values[0] == value

def test_update_replication(test_client):
    """Test that updates are replicated across regions"""
    key = "update_test"

    # Write initial value
    test_client.post("/write", json={"key": key, "value": "v1", "region": "us-east"})
    time.sleep(0.5)

    # Update value
    test_client.post("/write", json={"key": key, "value": "v2", "region": "us-east"})
    time.sleep(0.5)

    # Read from different region
    response = test_client.get(f"/read/{key}", headers={"X-Region": "eu-west"})
    assert response.status_code == 200
    assert response.json()["value"] == "v2"

def test_disaster_recovery_scenario(test_client):
    """Test disaster recovery by reading from alternate regions"""
    key = "dr_test"
    value = "dr_value"

    # Write to one region (replicates to all)
    test_client.post("/write", json={"key": key, "value": value, "region": "us-east"})
    time.sleep(1)

    # Try reading from any region - should work
    for region in ["us-east", "eu-west", "asia-pac"]:
        response = test_client.get(f"/read/{key}", headers={"X-Region": region})
        assert response.status_code == 200
        data = response.json()
        if data["success"]:  # At least one region should have the data
            assert data["value"] == value
            break
    else:
        pytest.fail("Data not found in any region")

def test_regional_isolation(test_client):
    """Test that each region maintains its own cache"""
    key = "isolation_test"

    # Write to US-EAST
    test_client.post("/write", json={"key": key, "value": "isolated", "region": "us-east"})

    # Read from US-EAST - caches in US-EAST
    response1 = test_client.get(f"/read/{key}", headers={"X-Region": "us-east"})
    response1_cached = test_client.get(f"/read/{key}", headers={"X-Region": "us-east"})
    assert response1_cached.json()["source"] == "cache"

    time.sleep(0.5)
    # Read from EU-WEST - first read will be from database (separate cache)
    response2 = test_client.get(f"/read/{key}", headers={"X-Region": "eu-west"})
    assert response2.json()["source"] == "database"
