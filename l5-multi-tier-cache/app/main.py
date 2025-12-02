from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse, StatsResponse
from app.database import init_pool, close_pool, init_db, get_db_connection, get_pool
from app.cache import init_caches, close_caches, get_from_cache, set_in_cache, invalidate_cache, get_cache_stats, clear_all_caches

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_pool()
    init_caches()
    init_db()

    yield

    # Shutdown
    close_pool()
    close_caches()

app = FastAPI(title="Layer 5 - Multi-Tier Caching", version="1.0.0", lifespan=lifespan)

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data to the database.
    Invalidates both L1 and L2 cache after write.
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

        # Invalidate both L1 and L2 cache
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
    Read data with multi-tier caching:
    1. Try L1 cache (in-process) - ~1μs
    2. Try L2 cache (Redis) - ~1-2ms
    3. Read from DB (L3) - ~10-20ms
    4. Populate L2 and L1 on cache miss
    """
    try:
        # Try multi-tier cache
        cached_data, cache_level = get_from_cache(key)
        if cached_data:
            return ReadResponse(
                success=True,
                key=cached_data['key'],
                value=cached_data['value'],
                created_at=cached_data.get('created_at'),
                updated_at=cached_data.get('updated_at'),
                cache_level=cache_level
            )

        # Cache miss - read from database (L3)
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT key, value, created_at, updated_at
                    FROM records
                    WHERE key = %s
                """, (key,))
                result = cur.fetchone()

        if result:
            # Store in both L1 and L2 cache for future reads
            result_dict = dict(result)
            set_in_cache(key, result_dict)

            return ReadResponse(
                success=True,
                key=result['key'],
                value=result['value'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                cache_level="L3"  # Read from database
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found",
                cache_level="L3"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get combined cache and pool statistics"""
    try:
        cache_stats = get_cache_stats()
        pool = get_pool()

        # L1 stats
        l1_hits = cache_stats.get("l1_hits", 0)
        l1_misses = cache_stats.get("l1_misses", 0)
        l1_total = l1_hits + l1_misses
        l1_hit_rate = (l1_hits / l1_total * 100) if l1_total > 0 else 0.0

        # L2 stats
        l2_hits = cache_stats.get("l2_hits", 0)
        l2_misses = cache_stats.get("l2_misses", 0)
        l2_total = l2_hits + l2_misses
        l2_hit_rate = (l2_hits / l2_total * 100) if l2_total > 0 else 0.0

        # Overall stats
        total_hits = l1_hits + l2_hits
        total_misses = l1_misses + l2_misses
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0

        return StatsResponse(
            l1_cache_available=cache_stats.get("l1_available", False),
            l1_cache_size=cache_stats.get("l1_size", 0),
            l1_cache_max_size=cache_stats.get("l1_max_size", 0),
            l1_cache_hits=l1_hits,
            l1_cache_misses=l1_misses,
            l1_hit_rate=round(l1_hit_rate, 2),
            l2_cache_available=cache_stats.get("l2_available", False),
            l2_cache_keys=cache_stats.get("l2_keys", 0),
            l2_cache_hits=l2_hits,
            l2_cache_misses=l2_misses,
            l2_hit_rate=round(l2_hit_rate, 2),
            db_pool_size=getattr(pool, 'min_size', 0) if pool else 0,
            total_hits=total_hits,
            total_misses=total_misses,
            overall_hit_rate=round(overall_hit_rate, 2)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.post("/clear-cache")
async def clear_cache():
    """Clear all cache data (L1 and L2)"""
    try:
        clear_all_caches()
        return {"success": True, "message": "All caches cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing caches: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Check caches
        cache_stats = get_cache_stats()

        return {
            "status": "healthy",
            "layer": "5-multi-tier-cache",
            "database": "healthy",
            "l1_cache": "healthy" if cache_stats.get("l1_available") else "unavailable",
            "l2_cache": "healthy" if cache_stats.get("l2_available") else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
