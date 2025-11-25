import pytest
from fastapi.testclient import TestClient

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "1-connection-pooling"

def test_pool_stats(client):
    """Test pool statistics endpoint"""
    response = client.get("/pool-stats")
    assert response.status_code == 200
    data = response.json()
    assert "pool_size" in data
    assert "pool_available" in data
    assert "requests_waiting" in data
    assert data["pool_size"] >= 0

def test_write_new_record(client):
    """Test writing a new record"""
    response = client.post("/write", json={"key": "test_key", "value": "test_value"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "test_key"
    assert data["message"] == "Data written successfully"

def test_write_update_existing_record(client):
    """Test updating an existing record"""
    # Write initial record
    client.post("/write", json={"key": "update_key", "value": "initial_value"})

    # Update the record
    response = client.post("/write", json={"key": "update_key", "value": "updated_value"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify the update
    read_response = client.get("/read/update_key")
    read_data = read_response.json()
    assert read_data["value"] == "updated_value"

def test_read_existing_record(client):
    """Test reading an existing record"""
    # Write a record first
    client.post("/write", json={"key": "read_key", "value": "read_value"})

    # Read the record
    response = client.get("/read/read_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "read_key"
    assert data["value"] == "read_value"
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

def test_read_nonexistent_record(client):
    """Test reading a non-existent record"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["key"] == "nonexistent_key"
    assert data["value"] is None
    assert data["message"] == "Key not found"

def test_concurrent_requests(client):
    """Test that connection pool handles concurrent requests"""
    import concurrent.futures

    def make_request(i):
        response = client.post("/write", json={"key": f"concurrent_{i}", "value": f"value_{i}"})
        return response.status_code == 200

    # Make 20 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(make_request, range(20)))

    # All requests should succeed
    assert all(results)

    # Verify all records were written
    for i in range(20):
        response = client.get(f"/read/concurrent_{i}")
        assert response.status_code == 200
        assert response.json()["success"] is True

def test_pool_reuses_connections(client):
    """Test that pool reuses connections efficiently"""
    # Get initial pool stats
    stats1 = client.get("/pool-stats").json()

    # Make several requests
    for i in range(5):
        client.post("/write", json={"key": f"pool_test_{i}", "value": f"value_{i}"})

    # Get pool stats again
    stats2 = client.get("/pool-stats").json()

    # Pool size should not have grown beyond max_size
    assert stats2["pool_size"] <= 10  # max_size from config

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

    # Verify all records
    for record in records:
        response = client.get(f"/read/{record['key']}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["value"] == record["value"]

def test_timestamps_update_on_write(client):
    """Test that timestamps are properly updated"""
    import time

    # Initial write
    client.post("/write", json={"key": "timestamp_key", "value": "initial"})
    response1 = client.get("/read/timestamp_key")
    data1 = response1.json()

    # Wait a moment
    time.sleep(0.1)

    # Update
    client.post("/write", json={"key": "timestamp_key", "value": "updated"})
    response2 = client.get("/read/timestamp_key")
    data2 = response2.json()

    # created_at should be the same, updated_at should be different
    assert data1["created_at"] == data2["created_at"]
    assert data1["updated_at"] != data2["updated_at"]
