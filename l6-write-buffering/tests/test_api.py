import pytest
import time
from tests.conftest import process_queue

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "6-write-buffering"
    assert data["database"] == "healthy"
    assert "queue_length" in data

def test_write_queues_data(client, sample_data):
    """Test that writes are queued"""
    response = client.post("/write", json=sample_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == sample_data["key"]
    assert data["queued"] is True
    assert "queued" in data["message"].lower()

def test_read_after_write_eventual_consistency(client, sample_data):
    """Test eventual consistency - write is queued but not immediately readable"""
    # Write data (queued)
    client.post("/write", json=sample_data)
    
    # Immediate read might not find it (eventual consistency)
    response = client.get(f"/read/{sample_data['key']}")
    # Could be not found or found depending on worker processing
    assert response.status_code == 200
    
    # Process queue manually
    process_queue()
    
    # Now it should be found
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["value"] == sample_data["value"]

def test_multiple_writes_queued(client):
    """Test multiple writes are queued"""
    for i in range(5):
        response = client.post("/write", json={"key": f"key_{i}", "value": f"value_{i}"})
        assert response.status_code == 200
        assert response.json()["queued"] is True
    
    # Process queue
    processed = process_queue()
    assert processed == 5
    
    # Verify all keys exist
    for i in range(5):
        response = client.get(f"/read/key_{i}")
        assert response.status_code == 200
        assert response.json()["value"] == f"value_{i}"

def test_cache_hit_after_processing(client, sample_data):
    """Test cache behavior with queued writes"""
    # Write (queued)
    client.post("/write", json=sample_data)
    
    # Process queue
    process_queue()
    
    # First read (cache miss)
    response1 = client.get(f"/read/{sample_data['key']}")
    assert response1.json()["from_cache"] is False
    
    # Second read (cache hit)
    response2 = client.get(f"/read/{sample_data['key']}")
    assert response2.json()["from_cache"] is True

def test_stats_endpoint(client):
    """Test stats endpoint returns queue information"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "queue_length" in data
    assert "writes_queued" in data
    assert "writes_processed" in data
    assert "cache_available" in data
    assert "db_pool_size" in data

def test_queue_length_increases_with_writes(client):
    """Test that queue length tracks queued writes"""
    # Write multiple items
    for i in range(3):
        client.post("/write", json={"key": f"queue_test_{i}", "value": f"value_{i}"})
    
    # Check queue length
    response = client.get("/stats")
    data = response.json()
    # Queue should have items (may have been processed already)
    assert data["writes_queued"] >= 3

def test_update_existing_key(client):
    """Test updating an existing key"""
    # Write initial value
    client.post("/write", json={"key": "update_test", "value": "initial"})
    process_queue()
    
    # Update value
    client.post("/write", json={"key": "update_test", "value": "updated"})
    process_queue()
    
    # Read updated value
    response = client.get("/read/update_test")
    assert response.status_code == 200
    assert response.json()["value"] == "updated"

def test_read_nonexistent_key(client):
    """Test reading a key that doesn't exist"""
    response = client.get("/read/nonexistent_key")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data.get("message", "").lower()

def test_cache_invalidation_on_write(client, sample_data):
    """Test that cache is invalidated when write is queued"""
    # Write and process
    client.post("/write", json=sample_data)
    process_queue()
    
    # Read to populate cache
    client.get(f"/read/{sample_data['key']}")
    
    # Update value
    new_data = {"key": sample_data["key"], "value": "new_value"}
    client.post("/write", json=new_data)
    process_queue()
    
    # Next read should get new value
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    assert response.json()["value"] == "new_value"

def test_timestamps_in_response(client, sample_data):
    """Test that timestamps are included"""
    client.post("/write", json=sample_data)
    process_queue()
    
    response = client.get(f"/read/{sample_data['key']}")
    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data

def test_special_characters_in_value(client):
    """Test special characters"""
    special_data = {
        "key": "special_test",
        "value": "Special: !@#$%^&*()"
    }
    client.post("/write", json=special_data)
    process_queue()
    
    response = client.get(f"/read/{special_data['key']}")
    assert response.status_code == 200
    assert response.json()["value"] == special_data["value"]

def test_long_value(client):
    """Test long values"""
    long_value = "x" * 10000
    client.post("/write", json={"key": "long_test", "value": long_value})
    process_queue()
    
    response = client.get(f"/read/long_test")
    assert response.status_code == 200
    assert len(response.json()["value"]) == 10000

def test_concurrent_writes(client):
    """Test concurrent write operations"""
    import concurrent.futures
    
    def write_data(i):
        response = client.post("/write", json={"key": f"concurrent_{i}", "value": f"value_{i}"})
        return response.status_code == 200
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_data, i) for i in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert all(results)
    
    # Process queue
    process_queue()
    process_queue()  # May need multiple batches
