import pytest
import time

def test_health(test_client):
    """Test health endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["layer"] == "10-enterprise-grade"
    assert "shards_healthy" in data
    assert "circuit_breakers" in data

def test_authentication_required(test_client):
    """Test that authentication is enforced"""
    # Without API key
    response = test_client.post("/write", json={"key": "test", "value": "test"})
    assert response.status_code == 401

def test_write_with_auth(test_client, api_headers):
    """Test write with proper authentication"""
    response = test_client.post(
        "/write",
        json={"key": "auth_test", "value": "authenticated"},
        headers=api_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "shard" in data
    assert data["cached"] is True

def test_read_with_cache(test_client, api_headers):
    """Test read with multi-tier caching"""
    key = "cache_test"

    # Write
    test_client.post("/write", json={"key": key, "value": "cached_value"}, headers=api_headers)

    # First read - from cache
    response1 = test_client.get(f"/read/{key}", headers=api_headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cache_hit"] is True
    assert data1["cache_level"] in ["L1", "L2"]

    # Second read - from L1 cache
    response2 = test_client.get(f"/read/{key}", headers=api_headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cache_level"] == "L1"

def test_database_sharding(test_client, api_headers):
    """Test that data is distributed across shards"""
    shards_used = set()

    for i in range(10):
        response = test_client.post(
            "/write",
            json={"key": f"shard_test_{i}", "value": f"value_{i}"},
            headers=api_headers
        )
        assert response.status_code == 200
        shards_used.add(response.json()["shard"])

    # Should use multiple shards
    assert len(shards_used) >= 2

def test_rate_limiting(test_client):
    """Test that rate limiting functionality is configured and exposed via stats"""
    # Test that rate limiter info is available in stats
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()

    # Verify rate limiting is configured
    assert "rate_limiting" in data
    assert data["rate_limiting"]["enabled"] is True
    assert data["rate_limiting"]["max_requests"] == 100
    assert data["rate_limiting"]["window_seconds"] == 60

    # Verify feature flag
    assert "features" in data
    assert data["features"]["rate_limiting"] is True

def test_circuit_breaker_info(test_client):
    """Test circuit breaker status"""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "circuit_breakers" in data
    assert "features" in data
    assert data["features"]["circuit_breakers"] is True

def test_metrics_endpoint(test_client):
    """Test Prometheus metrics endpoint"""
    response = test_client.get("/metrics")
    assert response.status_code == 200
    # Metrics should contain Prometheus format
    assert b"# HELP" in response.content

def test_stats_endpoint(test_client):
    """Test stats endpoint"""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "shards" in data
    assert "cache" in data
    assert "features" in data
    assert data["features"]["multi_tier_cache"] is True
    assert data["features"]["database_sharding"] is True

def test_write_and_read_flow(test_client, api_headers):
    """Test complete write and read flow"""
    key = "flow_test"
    value = "flow_value"

    # Write
    write_response = test_client.post(
        "/write",
        json={"key": key, "value": value},
        headers=api_headers
    )
    assert write_response.status_code == 200
    assert write_response.json()["success"] is True

    # Read
    read_response = test_client.get(f"/read/{key}", headers=api_headers)
    assert read_response.status_code == 200
    data = read_response.json()
    assert data["success"] is True
    assert data["value"] == value
    assert "latency_ms" in data

def test_not_found(test_client, api_headers):
    """Test reading non-existent key"""
    response = test_client.get("/read/nonexistent_12345", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["message"].lower()
