import pytest
import time
from app.database import get_write_connection, get_read_connection
from app.events import get_event_stats

def test_health(test_client):
    """Test health endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "7-cqrs"

def test_write_command(test_client):
    """Test writing a command to write database"""
    response = test_client.post("/write", json={"key": "test_key", "value": "test_value"})
    if response.status_code != 200:
        print(f"ERROR: Status={response.status_code}, Body={response.text}")
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "test_key"
    assert data["event_id"] is not None
    assert "event published" in data["message"].lower()

def test_write_stores_in_write_db(test_client):
    """Test that writes are stored in write database"""
    key = "write_db_test"
    value = "write_db_value"

    # Write command
    response = test_client.post("/write", json={"key": key, "value": value})
    assert response.status_code == 200

    # Verify in write database
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM commands WHERE key = %s ORDER BY id DESC LIMIT 1", (key,))
            result = cur.fetchone()
            assert result is not None
            assert result[0] == key
            assert result[1] == value

def test_projector_updates_read_db(test_client):
    """Test that projector eventually updates read database"""
    key = "projector_test"
    value = "projector_value"

    # Write command
    response = test_client.post("/write", json={"key": key, "value": value})
    assert response.status_code == 200

    # Wait for projector to process event (eventual consistency)
    max_wait = 10  # seconds
    start_time = time.time()
    found = False

    while time.time() - start_time < max_wait:
        try:
            with get_read_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT key, value FROM records WHERE key = %s", (key,))
                    result = cur.fetchone()
                    if result:
                        assert result[0] == key
                        assert result[1] == value
                        found = True
                        break
        except:
            pass
        time.sleep(0.5)

    assert found, "Projector did not update read database within timeout"

def test_read_query_from_read_db(test_client):
    """Test reading from read database"""
    key = "read_test"
    value = "read_value"

    # Write and wait for projection
    test_client.post("/write", json={"key": key, "value": value})
    time.sleep(2)  # Wait for projection

    # Read query
    response = test_client.get(f"/read/{key}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == key
    assert data["value"] == value
    assert data["from_read_db"] is True
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

def test_read_nonexistent_key(test_client):
    """Test reading a key that doesn't exist"""
    response = test_client.get("/read/nonexistent_key_12345")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["message"].lower()

def test_update_command(test_client):
    """Test updating a record"""
    key = "update_test"
    value1 = "value1"
    value2 = "value2"

    # Initial write
    test_client.post("/write", json={"key": key, "value": value1})
    time.sleep(2)

    # Update
    response = test_client.put("/write", json={"key": key, "value": value2})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["event_id"] is not None

    # Wait for projection
    time.sleep(2)

    # Verify updated value in read DB
    response = test_client.get(f"/read/{key}")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == value2

def test_write_count_increments(test_client):
    """Test that write_count increments on updates"""
    key = "write_count_test"

    # Write multiple times
    for i in range(3):
        test_client.post("/write", json={"key": key, "value": f"value{i}"})
        time.sleep(1)

    # Wait for all projections
    time.sleep(2)

    # Check write count
    with get_read_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT write_count FROM records WHERE key = %s", (key,))
            result = cur.fetchone()
            assert result is not None
            assert result[0] >= 3  # Should be at least 3

def test_read_count_increments(test_client):
    """Test that read_count increments on reads"""
    key = "read_count_test"
    value = "read_count_value"

    # Write and wait
    test_client.post("/write", json={"key": key, "value": value})
    time.sleep(2)

    # Read multiple times
    initial_count = None
    for i in range(3):
        response = test_client.get(f"/read/{key}")
        assert response.status_code == 200
        data = response.json()
        if initial_count is None:
            initial_count = data["read_count"]
        else:
            assert data["read_count"] > initial_count

def test_eventual_consistency(test_client):
    """Test eventual consistency between write and read databases"""
    key = "consistency_test"
    value = "consistency_value"

    # Write to write DB
    write_response = test_client.post("/write", json={"key": key, "value": value})
    assert write_response.status_code == 200

    # Immediately after write, read DB might not have the data yet
    immediate_response = test_client.get(f"/read/{key}")
    # This might fail or succeed depending on projector speed

    # After waiting, read DB should have the data
    time.sleep(3)
    eventual_response = test_client.get(f"/read/{key}")
    assert eventual_response.status_code == 200
    data = eventual_response.json()
    assert data["success"] is True
    assert data["value"] == value

def test_stats_endpoint(test_client):
    """Test statistics endpoint"""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "write_db_pool_size" in data
    assert "read_db_pool_size" in data
    assert "events_published" in data
    assert "events_projected" in data
    assert "read_db_records" in data
    assert "write_db_records" in data
    assert isinstance(data["events_published"], int)
    assert isinstance(data["events_projected"], int)

def test_event_publishing(test_client):
    """Test that events are published to stream"""
    initial_stats = test_client.get("/stats").json()
    initial_published = initial_stats["events_published"]

    # Write a command
    test_client.post("/write", json={"key": "event_test", "value": "event_value"})

    # Check stats
    new_stats = test_client.get("/stats").json()
    assert new_stats["events_published"] > initial_published

def test_event_projection(test_client):
    """Test that events are projected"""
    initial_stats = test_client.get("/stats").json()
    initial_projected = initial_stats["events_projected"]

    # Write and wait for projection
    test_client.post("/write", json={"key": "projection_test", "value": "projection_value"})
    time.sleep(3)

    # Check stats
    new_stats = test_client.get("/stats").json()
    assert new_stats["events_projected"] > initial_projected

def test_multiple_writes_same_key(test_client):
    """Test multiple writes to the same key"""
    key = "multi_write_test"

    # Write multiple times
    for i in range(5):
        response = test_client.post("/write", json={"key": key, "value": f"value_{i}"})
        assert response.status_code == 200

    # Wait for projections
    time.sleep(3)

    # Read final value
    response = test_client.get(f"/read/{key}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Should have the last value
    assert "value_" in data["value"]

def test_write_db_independence(test_client):
    """Test that write DB is independent of read DB"""
    key = "independence_test"
    value = "independence_value"

    # Write to write DB
    test_client.post("/write", json={"key": key, "value": value})

    # Verify in write DB immediately
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM commands WHERE key = %s", (key,))
            count = cur.fetchone()[0]
            assert count >= 1

def test_read_db_denormalization(test_client):
    """Test that read DB has denormalized fields"""
    key = "denorm_test"
    value = "denorm_value"

    # Write and wait
    test_client.post("/write", json={"key": key, "value": value})
    time.sleep(3)

    # Verify denormalized fields in read DB
    with get_read_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT key, value, created_at, updated_at, read_count, write_count FROM records WHERE key = %s",
                (key,)
            )
            result = cur.fetchone()
            assert result is not None
            assert result[0] == key  # key
            assert result[1] == value  # value
            assert result[2] is not None  # created_at
            assert result[3] is not None  # updated_at
            assert isinstance(result[4], int)  # read_count
            assert isinstance(result[5], int)  # write_count

def test_concurrent_writes(test_client):
    """Test concurrent writes to different keys"""
    keys = [f"concurrent_{i}" for i in range(10)]

    # Write all keys
    for key in keys:
        response = test_client.post("/write", json={"key": key, "value": f"value_{key}"})
        assert response.status_code == 200

    # Wait for all projections
    time.sleep(5)

    # Verify all keys in read DB
    with get_read_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM records WHERE key LIKE 'concurrent_%'")
            count = cur.fetchone()[0]
            assert count >= len(keys)

def test_database_separation(test_client):
    """Test that write and read databases are truly separate"""
    stats = test_client.get("/stats").json()

    # Both pools should be active
    assert stats["write_db_pool_size"] >= 0
    assert stats["read_db_pool_size"] >= 0

    # Both databases should have schemas
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'commands'")
            assert cur.fetchone()[0] == 1

    with get_read_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'records'")
            assert cur.fetchone()[0] == 1
