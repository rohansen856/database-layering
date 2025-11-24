import pytest
from app.database import get_db_connection, init_db

def test_database_connection():
    """Test that we can connect to the database"""
    with get_db_connection() as conn:
        assert conn is not None
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            assert result[0] == 1

def test_table_exists():
    """Test that the records table exists"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'records'
                )
            """)
            exists = cur.fetchone()[0]
            assert exists is True

def test_table_schema():
    """Test that the records table has the correct schema"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'records'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()

            column_dict = {col[0]: col[1] for col in columns}

            assert 'id' in column_dict
            assert 'key' in column_dict
            assert 'value' in column_dict
            assert 'created_at' in column_dict
            assert 'updated_at' in column_dict

def test_index_exists():
    """Test that the index on key column exists"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE tablename = 'records' AND indexname = 'idx_records_key'
                )
            """)
            exists = cur.fetchone()[0]
            assert exists is True

def test_unique_constraint_on_key():
    """Test that the key column has a unique constraint"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Insert a record
            cur.execute("""
                INSERT INTO records (key, value) VALUES (%s, %s)
            """, ("unique_test", "value1"))
            conn.commit()

            # Try to insert duplicate key - should fail
            with pytest.raises(Exception):
                cur.execute("""
                    INSERT INTO records (key, value) VALUES (%s, %s)
                """, ("unique_test", "value1"))
                conn.commit()
