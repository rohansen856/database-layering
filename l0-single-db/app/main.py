from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse
from app.database import init_db, get_db_connection
import psycopg

app = FastAPI(title="Layer 0 - Single DB", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data to the database.
    If key exists, update the value. Otherwise, insert new record.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO records (key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP
                """, (request.key, request.value))
                conn.commit()

        return WriteResponse(
            success=True,
            key=request.key,
            message="Data written successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/read/{key}", response_model=ReadResponse)
async def read_data(key: str):
    """
    Read data from the database by key.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT key, value, created_at, updated_at
                    FROM records
                    WHERE key = %s
                """, (key,))
                result = cur.fetchone()

        if result:
            return ReadResponse(
                success=True,
                key=result['key'],
                value=result['value'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "layer": "0-single-db"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")
