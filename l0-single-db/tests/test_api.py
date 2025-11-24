import pytest
from fastapi.testclient import TestClient

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "0-single-db"

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

def test_write_empty_value(client):
    """Test writing a record with empty value"""
    response = client.post("/write", json={"key": "empty_key", "value": ""})
    assert response.status_code == 200

    # Verify it was stored
    read_response = client.get("/read/empty_key")
    assert read_response.json()["value"] == ""

def test_write_large_value(client):
    """Test writing a record with large value"""
    large_value = "x" * 10000  # 10KB string
    response = client.post("/write", json={"key": "large_key", "value": large_value})
    assert response.status_code == 200

    # Verify it was stored correctly
    read_response = client.get("/read/large_key")
    assert read_response.json()["value"] == large_value

def test_write_special_characters(client):
    """Test writing a record with special characters"""
    special_value = "Hello 世界! @#$%^&*()_+-={}[]|:;<>?,./~`"
    response = client.post("/write", json={"key": "special_key", "value": special_value})
    assert response.status_code == 200

    # Verify it was stored correctly
    read_response = client.get("/read/special_key")
    assert read_response.json()["value"] == special_value

def test_concurrent_writes_same_key(client):
    """Test concurrent writes to the same key"""
    # Simulate concurrent updates
    for i in range(10):
        response = client.post("/write", json={"key": "concurrent_key", "value": f"value_{i}"})
        assert response.status_code == 200

    # The last write should win
    read_response = client.get("/read/concurrent_key")
    assert read_response.status_code == 200
    assert read_response.json()["success"] is True

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

def test_read_url_encoded_key(client):
    """Test reading with URL-encoded special characters in key"""
    key_with_space = "key with space"
    client.post("/write", json={"key": key_with_space, "value": "test_value"})

    response = client.get(f"/read/{key_with_space}")
    assert response.status_code == 200
    assert response.json()["success"] is True
