import pytest
from app.sharding import get_shard_id, get_shard_stats
from app.database import get_shard_connection
from psycopg.rows import dict_row

def test_shard_id_consistency():
    """Test that same key always returns same shard"""
    key = "consistent_key"
    shard_1 = get_shard_id(key)
    shard_2 = get_shard_id(key)
    shard_3 = get_shard_id(key)

    assert shard_1 == shard_2 == shard_3
    assert 0 <= shard_1 < 3

def test_shard_id_distribution():
    """Test that different keys distribute across shards"""
    shard_counts = {0: 0, 1: 0, 2: 0}

    # Generate many keys and check distribution
    for i in range(100):
        key = f"dist_key_{i}"
        shard_id = get_shard_id(key)
        shard_counts[shard_id] += 1

    # Each shard should get some keys (not perfect distribution, but should be reasonable)
    for shard_id in range(3):
        assert shard_counts[shard_id] > 0
        # With 100 keys and 3 shards, expect roughly 33 per shard (allow 10-60 range)
        assert 10 < shard_counts[shard_id] < 60

def test_shard_id_deterministic():
    """Test that shard assignment is deterministic"""
    test_keys = [
        "user:123",
        "product:456",
        "order:789",
        "session:abc",
        "cart:def"
    ]

    # Store shard assignments
    assignments = {}
    for key in test_keys:
        assignments[key] = get_shard_id(key)

    # Verify consistency over multiple calls
    for _ in range(10):
        for key in test_keys:
            assert get_shard_id(key) == assignments[key]

def test_write_to_correct_shard():
    """Test that data is written to the correct shard"""
    test_key = "shard_test_key"
    test_value = "shard_test_value"
    expected_shard = get_shard_id(test_key)

    # Write to determined shard
    with get_shard_connection(expected_shard) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (key, value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (test_key, test_value))
            conn.commit()

    # Verify data exists in correct shard
    with get_shard_connection(expected_shard) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT key, value FROM records WHERE key = %s", (test_key,))
            result = cur.fetchone()

    assert result is not None
    assert result['key'] == test_key
    assert result['value'] == test_value

    # Verify data does NOT exist in other shards
    for shard_id in range(3):
        if shard_id == expected_shard:
            continue

        with get_shard_connection(shard_id) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT key, value FROM records WHERE key = %s", (test_key,))
                result = cur.fetchone()

        assert result is None

def test_shard_isolation():
    """Test that shards are isolated from each other"""
    # Write to each shard
    for shard_id in range(3):
        key = f"shard_{shard_id}_key"
        value = f"shard_{shard_id}_value"

        with get_shard_connection(shard_id) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO records (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, (key, value))
                conn.commit()

    # Verify each shard has only its own data
    for shard_id in range(3):
        with get_shard_connection(shard_id) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT key FROM records")
                results = cur.fetchall()

        # Should have at least one record
        assert len(results) >= 1

        # Check that the record belongs to this shard
        for result in results:
            key_shard = get_shard_id(result['key'])
            # The record might not be ours if it was written by other tests
            # but if it has the pattern we created, verify it's in the right shard
            if result['key'].startswith('shard_'):
                expected_shard = int(result['key'].split('_')[1])
                assert expected_shard == shard_id

def test_get_shard_stats():
    """Test shard statistics function"""
    # Write some data to different shards
    for i in range(15):
        key = f"stat_key_{i}"
        shard_id = get_shard_id(key)

        with get_shard_connection(shard_id) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO records (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, (key, f"value_{i}"))
                conn.commit()

    # Get stats
    stats = get_shard_stats()

    # Verify stats structure
    assert "shard_0" in stats
    assert "shard_1" in stats
    assert "shard_2" in stats

    # Verify total count
    total_count = sum(stats.values())
    assert total_count == 15

def test_multiple_keys_same_shard():
    """Test writing multiple keys to the same shard"""
    # Find keys that hash to the same shard
    target_shard = 0
    keys_for_shard = []

    for i in range(100):
        key = f"multi_shard_key_{i}"
        if get_shard_id(key) == target_shard:
            keys_for_shard.append(key)
            if len(keys_for_shard) >= 5:
                break

    # Write all keys
    for key in keys_for_shard:
        with get_shard_connection(target_shard) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO records (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, (key, f"value_for_{key}"))
                conn.commit()

    # Verify all keys exist in the shard
    with get_shard_connection(target_shard) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            placeholders = ','.join(['%s'] * len(keys_for_shard))
            cur.execute(f"""
                SELECT key FROM records
                WHERE key IN ({placeholders})
            """, keys_for_shard)
            results = cur.fetchall()

    assert len(results) == len(keys_for_shard)

def test_shard_range():
    """Test that shard IDs are always in valid range"""
    test_keys = [
        "",  # Edge case: empty string
        "a",  # Single character
        "very_long_key_" * 100,  # Very long key
        "special!@#$%^&*()chars",  # Special characters
        "unicode_测试_key",  # Unicode
        "123456789",  # Numeric string
    ]

    for key in test_keys:
        shard_id = get_shard_id(key)
        assert 0 <= shard_id < 3, f"Shard ID {shard_id} out of range for key: {key}"

def test_hash_based_distribution_balance():
    """Test that hash-based sharding provides reasonable balance"""
    shard_counts = {0: 0, 1: 0, 2: 0}

    # Generate 300 keys and check distribution
    for i in range(300):
        key = f"balance_key_{i}"
        shard_id = get_shard_id(key)
        shard_counts[shard_id] += 1

    # With 300 keys and 3 shards, expect roughly 100 per shard
    # Allow 60-140 range (40% deviation)
    for shard_id in range(3):
        assert 60 <= shard_counts[shard_id] <= 140, \
            f"Shard {shard_id} has {shard_counts[shard_id]} keys (expected 60-140)"

    # Total should be 300
    assert sum(shard_counts.values()) == 300
