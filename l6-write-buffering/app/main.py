from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse, StatsResponse
from app.database import init_pool, close_pool, init_db, get_db_connection, get_pool
from app.cache import init_redis, close_redis, get_from_cache, set_in_cache, invalidate_cache, get_cache_stats
from app.queue import init_queue, close_queue, enqueue_write, get_queue_stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_pool()
    init_redis()
    init_queue()
    init_db()

    yield

    # Shutdown
    close_pool()
    close_redis()
    close_queue()

app = FastAPI(title="Layer 6 - Write Buffering / Async Writes", version="1.0.0", lifespan=lifespan)

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data asynchronously using a queue.
    Writes are queued and processed by a background worker.
    Returns immediately without waiting for database write.
    """
    try:
        # Enqueue the write operation
        queued = enqueue_write(request.key, request.value)

        if queued:
            # Invalidate cache immediately (eventual consistency)
            invalidate_cache(request.key)

            return WriteResponse(
                success=True,
                key=request.key,
                queued=True,
                message="Write queued successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to queue write")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue error: {str(e)}")

@app.get("/read/{key}", response_model=ReadResponse)
async def read_data(key: str):
    """
    Read data with caching:
    1. Try cache first
    2. If miss, read from database
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
            result_dict = dict(result)
            set_in_cache(key, result_dict)

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

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get combined cache, pool, and queue statistics"""
    try:
        cache_stats = get_cache_stats()
        queue_stats = get_queue_stats()
        pool = get_pool()

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
            db_pool_size=getattr(pool, 'min_size', 0) if pool else 0,
            queue_length=queue_stats.get("queue_length", 0),
            writes_queued=queue_stats.get("writes_queued", 0),
            writes_processed=queue_stats.get("writes_processed", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Check cache
        cache_available = get_cache_stats().get("available", False)

        # Check queue
        queue_stats = get_queue_stats()

        return {
            "status": "healthy",
            "layer": "6-write-buffering",
            "database": "healthy",
            "cache": "healthy" if cache_available else "unavailable",
            "queue": "healthy",
            "queue_length": queue_stats.get("queue_length", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
