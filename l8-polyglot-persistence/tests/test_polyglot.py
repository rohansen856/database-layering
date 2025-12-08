import pytest
import time
from app.postgres_db import get_connection, get_transaction_count
from app.mongodb import get_collection, get_document_count
from app.cache import cache_get, cache_keys_count

def test_health(test_client):
    """Test health endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["layer"] == "8-polyglot-persistence"
    assert "PostgreSQL" in data["databases"]
    assert "MongoDB" in data["databases"]
    assert "Redis" in data["databases"]

def test_write_transaction_to_postgres(test_client):
    """Test writing transactional data to PostgreSQL"""
    response = test_client.post("/write/transaction", json={
        "user_id": "user123",
        "amount": 99.99,
        "transaction_type": "purchase"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["transaction_id"] is not None
    assert data["stored_in"] == "PostgreSQL"

def test_write_document_to_mongodb(test_client):
    """Test writing document to MongoDB"""
    response = test_client.post("/write/document", json={
        "key": "user_profile_123",
        "data": {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "preferences": {
                "theme": "dark",
                "notifications": True
            }
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "user_profile_123"
    assert data["stored_in"] == "MongoDB"

def test_read_transaction_from_postgres(test_client):
    """Test reading transactions from PostgreSQL"""
    # Write a transaction first
    test_client.post("/write/transaction", json={
        "user_id": "user456",
        "amount": 50.00,
        "transaction_type": "refund"
    })

    # Read transactions
    response = test_client.get("/read/transaction/user456")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "user456"
    assert isinstance(data["value"], list)
    assert len(data["value"]) >= 1
    assert data["source"] == "postgres"

def test_read_transaction_from_cache(test_client):
    """Test reading transactions from cache on second request"""
    user_id = "user789"

    # Write a transaction
    test_client.post("/write/transaction", json={
        "user_id": user_id,
        "amount": 25.00,
        "transaction_type": "purchase"
    })

    # First read - from database
    response1 = test_client.get(f"/read/transaction/{user_id}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["source"] == "postgres"

    # Second read - from cache
    response2 = test_client.get(f"/read/transaction/{user_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["source"] == "cache"

def test_read_document_from_mongodb(test_client):
    """Test reading document from MongoDB"""
    # Write a document first
    test_client.post("/write/document", json={
        "key": "product_001",
        "data": {
            "name": "Laptop",
            "price": 999.99,
            "specs": {
                "ram": "16GB",
                "storage": "512GB SSD"
            }
        }
    })

    # Read document
    response = test_client.get("/read/document/product_001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key"] == "product_001"
    assert data["data"]["name"] == "Laptop"
    assert data["stored_in"] == "MongoDB"

def test_read_document_from_cache(test_client):
    """Test reading document from cache on second request"""
    # Write a document
    test_client.post("/write/document", json={
        "key": "product_002",
        "data": {"name": "Mouse", "price": 29.99}
    })

    # First read - from MongoDB
    response1 = test_client.get("/read/document/product_002")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["from_cache"] is False

    # Second read - from cache
    response2 = test_client.get("/read/document/product_002")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["from_cache"] is True
    assert data2["stored_in"] == "Redis (cache)"

def test_document_cache_invalidation(test_client):
    """Test that writing invalidates the cache"""
    key = "product_003"

    # Write document
    test_client.post("/write/document", json={
        "key": key,
        "data": {"name": "Keyboard", "price": 79.99}
    })

    # Read to populate cache
    response1 = test_client.get(f"/read/document/{key}")
    assert response1.json()["from_cache"] is False

    # Read again from cache
    response2 = test_client.get(f"/read/document/{key}")
    assert response2.json()["from_cache"] is True

    # Update document (should invalidate cache)
    test_client.post("/write/document", json={
        "key": key,
        "data": {"name": "Mechanical Keyboard", "price": 129.99}
    })

    # Read again - should be from MongoDB (cache was invalidated)
    response3 = test_client.get(f"/read/document/{key}")
    assert response3.json()["from_cache"] is False
    assert response3.json()["data"]["name"] == "Mechanical Keyboard"

def test_flexible_schema_mongodb(test_client):
    """Test MongoDB's flexible schema capability"""
    # Write documents with different schemas
    test_client.post("/write/document", json={
        "key": "schema_test_1",
        "data": {"field_a": "value1", "field_b": 123}
    })

    test_client.post("/write/document", json={
        "key": "schema_test_2",
        "data": {"field_a": "value2", "field_c": [1, 2, 3], "nested": {"x": "y"}}
    })

    # Both should be successfully stored despite different schemas
    response1 = test_client.get("/read/document/schema_test_1")
    response2 = test_client.get("/read/document/schema_test_2")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["data"]["field_b"] == 123
    assert response2.json()["data"]["field_c"] == [1, 2, 3]

def test_postgres_acid_transactions(test_client):
    """Test PostgreSQL ACID compliance for transactions"""
    user_id = "acid_user"

    # Write multiple transactions
    for i in range(5):
        response = test_client.post("/write/transaction", json={
            "user_id": user_id,
            "amount": 10.00 * (i + 1),
            "transaction_type": "purchase"
        })
        assert response.status_code == 200

    # Read all transactions
    response = test_client.get(f"/read/transaction/{user_id}")
    assert response.status_code == 200
    transactions = response.json()["value"]
    assert len(transactions) >= 5

def test_stats_endpoint(test_client):
    """Test statistics endpoint"""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "postgres_pool_size" in data
    assert "mongodb_connections" in data
    assert "cache_keys" in data
    assert "total_transactions" in data
    assert "total_documents" in data
    assert isinstance(data["total_transactions"], int)
    assert isinstance(data["total_documents"], int)

def test_multiple_databases_working(test_client):
    """Test that all three databases are working together"""
    # Write to PostgreSQL
    trans_response = test_client.post("/write/transaction", json={
        "user_id": "multi_test",
        "amount": 100.00,
        "transaction_type": "purchase"
    })
    assert trans_response.status_code == 200

    # Write to MongoDB
    doc_response = test_client.post("/write/document", json={
        "key": "multi_test_doc",
        "data": {"test": "value"}
    })
    assert doc_response.status_code == 200

    # Check stats to verify all databases have data
    stats = test_client.get("/stats").json()
    assert stats["total_transactions"] > 0
    assert stats["total_documents"] > 0
    assert stats["cache_keys"] >= 0

def test_postgres_data_integrity(test_client):
    """Test PostgreSQL data integrity"""
    user_id = "integrity_test"
    amount = 123.45

    # Write transaction
    write_response = test_client.post("/write/transaction", json={
        "user_id": user_id,
        "amount": amount,
        "transaction_type": "transfer"
    })
    transaction_id = write_response.json()["transaction_id"]

    # Verify data directly in database
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, amount FROM transactions WHERE id = %s", (transaction_id,))
            result = cur.fetchone()
            assert result is not None
            assert result[0] == user_id
            assert float(result[1]) == amount

def test_mongodb_data_persistence(test_client):
    """Test MongoDB data persistence"""
    key = "persistence_test"
    data = {"field1": "value1", "field2": 42}

    # Write to MongoDB
    test_client.post("/write/document", json={"key": key, "data": data})

    # Verify directly in MongoDB
    col = get_collection()
    doc = col.find_one({"key": key})
    assert doc is not None
    assert doc["data"]["field1"] == "value1"
    assert doc["data"]["field2"] == 42

def test_read_nonexistent_transaction(test_client):
    """Test reading transactions for nonexistent user"""
    response = test_client.get("/read/transaction/nonexistent_user_12345")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "found" in data["message"].lower() or "no transactions" in data["message"].lower()

def test_read_nonexistent_document(test_client):
    """Test reading nonexistent document"""
    response = test_client.get("/read/document/nonexistent_doc_12345")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

def test_concurrent_writes_different_dbs(test_client):
    """Test concurrent writes to different databases"""
    # Write to both databases in quick succession
    for i in range(10):
        test_client.post("/write/transaction", json={
            "user_id": f"concurrent_user_{i}",
            "amount": 10.00,
            "transaction_type": "purchase"
        })
        test_client.post("/write/document", json={
            "key": f"concurrent_doc_{i}",
            "data": {"index": i}
        })

    # Verify stats show increased counts
    stats = test_client.get("/stats").json()
    assert stats["total_transactions"] >= 10
    assert stats["total_documents"] >= 10

def test_cache_ttl_behavior(test_client):
    """Test cache TTL for transactional data"""
    user_id = "ttl_test_user"

    # Write transaction
    test_client.post("/write/transaction", json={
        "user_id": user_id,
        "amount": 50.00,
        "transaction_type": "purchase"
    })

    # First read - populate cache
    response1 = test_client.get(f"/read/transaction/{user_id}")
    assert response1.json()["source"] == "postgres"

    # Second read - from cache
    response2 = test_client.get(f"/read/transaction/{user_id}")
    assert response2.json()["source"] == "cache"

    # Note: Full TTL testing would require waiting 60+ seconds
