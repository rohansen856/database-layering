"""PostgreSQL database for transactional data (ACID compliance)"""
import psycopg
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from app.config import settings

pool = None

def init_pool():
    """Initialize PostgreSQL connection pool"""
    global pool
    pool = ConnectionPool(
        conninfo=settings.postgres_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size
    )
    print("PostgreSQL pool initialized")

def close_pool():
    """Close PostgreSQL connection pool"""
    global pool
    if pool:
        pool.close()
        print("PostgreSQL pool closed")

def get_pool():
    """Get current pool instance"""
    return pool

@contextmanager
def get_connection():
    """Get a connection from the pool"""
    if not pool:
        raise ValueError("PostgreSQL pool not initialized")
    with pool.connection() as conn:
        yield conn

def init_schema():
    """Initialize PostgreSQL schema for transactions"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create transactions table (ACID-compliant)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_user_id
                ON transactions(user_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_created_at
                ON transactions(created_at DESC)
            """)
            conn.commit()
    print("PostgreSQL schema initialized")

def write_transaction(user_id: str, amount: float, transaction_type: str) -> int:
    """Write a transaction to PostgreSQL"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO transactions (user_id, amount, transaction_type) VALUES (%s, %s, %s) RETURNING id",
                (user_id, amount, transaction_type)
            )
            transaction_id = cur.fetchone()[0]
            conn.commit()
    return transaction_id

def get_user_transactions(user_id: str):
    """Get all transactions for a user"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, amount, transaction_type, created_at FROM transactions WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            results = cur.fetchall()
    return results

def get_transaction_count() -> int:
    """Get total number of transactions"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transactions")
            count = cur.fetchone()[0]
    return count
