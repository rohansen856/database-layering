from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse, CacheStatsResponse
from app.database import init_pool, close_pool, init_db, get_db_connection
from app.cache import init_redis, close_redis, get_from_cache, set_in_cache, invalidate_cache, get_cache_stats
import psycopg

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_pool()
    init_redis()
    init_db()
    yield
    # Shutdown
    close_pool()
    close_redis()

app = FastAPI(title="Layer 2 - Read Cache (Cache-Aside)", version="1.0.0", lifespan=lifespan)

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data to the database.
    Implements cache-aside pattern: write to DB, then invalidate cache.
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

        # Invalidate cache after write
        invalidate_cache(request.key)

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
    Read data with cache-aside pattern:
    1. Try cache first
    2. If miss, read from DB
    3. Store in cache for future reads
    """
    try:
        # Try cache first
        cached_data = get_from_cache(key)
        if cached_data:
            return ReadResponse(
                success=True,
                key=cached_data['key'],
                value=cached_data['value'],
                created_at=cached_data.get('created_at'),
                updated_at=cached_data.get('updated_at'),
                from_cache=True
            )

        # Cache miss - read from database
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT key, value, created_at, updated_at
                    FROM records
                    WHERE key = %s
                """, (key,))
                result = cur.fetchone()

        if result:
            # Store in cache for future reads
            set_in_cache(key, dict(result))

            return ReadResponse(
                success=True,
                key=result['key'],
                value=result['value'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                from_cache=False
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found",
                from_cache=False
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/cache-stats", response_model=CacheStatsResponse)
async def cache_stats():
    """Get cache statistics"""
    try:
        stats = get_cache_stats()

        if not stats.get("available"):
            return CacheStatsResponse(available=False)

        hits = stats.get("hits", 0)
        misses = stats.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return CacheStatsResponse(
            available=True,
            hits=hits,
            misses=misses,
            keys=stats.get("keys", 0),
            hit_rate=round(hit_rate, 2)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Check Redis
        cache_available = get_cache_stats().get("available", False)

        return {
            "status": "healthy",
            "layer": "2-read-cache",
            "database": "healthy",
            "cache": "healthy" if cache_available else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
