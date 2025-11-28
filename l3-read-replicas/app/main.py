from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse, StatsResponse
from app.database import init_pools, close_pools, init_db, get_primary_connection, get_replica_connection, get_primary_pool, get_replica_pool
from app.cache import init_redis, close_redis, get_from_cache, set_in_cache, invalidate_cache, get_cache_stats
import psycopg
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_pools()
    init_redis()

    # Wait a bit for replica to sync
    time.sleep(2)
    init_db()

    yield
    # Shutdown
    close_pools()
    close_redis()

app = FastAPI(title="Layer 3 - Read Replicas + Cache", version="1.0.0", lifespan=lifespan)

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data to the PRIMARY database.
    Invalidates cache after write.
    """
    try:
        with get_primary_connection() as conn:
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
            message="Data written successfully to primary"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/read/{key}", response_model=ReadResponse)
async def read_data(key: str):
    """
    Read data with cache and replica:
    1. Try cache first
    2. If miss, read from REPLICA
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
                from_cache=True,
                from_replica=False
            )

        # Cache miss - read from REPLICA
        with get_replica_connection() as conn:
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
                from_cache=False,
                from_replica=True
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found",
                from_cache=False,
                from_replica=True
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get combined cache and pool statistics"""
    try:
        cache_stats = get_cache_stats()
        primary_pool = get_primary_pool()
        replica_pool = get_replica_pool()

        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return StatsResponse(
            cache_available=cache_stats.get("available", False),
            cache_hits=hits if cache_stats.get("available") else None,
            cache_misses=misses if cache_stats.get("available") else None,
            cache_keys=cache_stats.get("keys", 0) if cache_stats.get("available") else None,
            cache_hit_rate=round(hit_rate, 2) if cache_stats.get("available") else None,
            primary_pool_size=getattr(primary_pool, 'min_size', 0) if primary_pool else 0,
            replica_pool_size=getattr(replica_pool, 'min_size', 0) if replica_pool else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check primary database
        with get_primary_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Check replica database
        with get_replica_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Check Redis
        cache_available = get_cache_stats().get("available", False)

        return {
            "status": "healthy",
            "layer": "3-read-replicas",
            "primary": "healthy",
            "replica": "healthy",
            "cache": "healthy" if cache_available else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
