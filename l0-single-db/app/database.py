import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
from app.config import settings

def init_db():
    """Initialize database schema"""
    conn = psycopg.connect(settings.database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_key ON records(key)
            """)
            conn.commit()
    finally:
        conn.close()

@contextmanager
def get_db_connection():
    """Get a database connection"""
    conn = psycopg.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()
