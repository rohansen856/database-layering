from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from app.models import WriteRequest, WriteResponse, ReadResponse, StatsResponse
from app.database import init_shard_pools, close_shard_pools, init_db, get_shard_connection, get_shard_pool
from app.cache import init_redis, close_redis, get_from_cache, set_in_cache, invalidate_cache, get_cache_stats
from app.sharding import get_shard_id, get_shard_stats
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_shard_pools()
    init_redis()
    init_db()

    yield

    # Shutdown
    close_shard_pools()
    close_redis()

app = FastAPI(title="Layer 4 - DB Sharding + Cache", version="1.0.0", lifespan=lifespan)

@app.post("/write", response_model=WriteResponse)
async def write_data(request: WriteRequest):
    """
    Write data using hash-based sharding.
    Routes the key to appropriate shard.
    Invalidates cache after write.
    """
    try:
        # Determine which shard to use
        shard_id = get_shard_id(request.key)

        # Write to the appropriate shard
        with get_shard_connection(shard_id) as conn:
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
            shard_id=shard_id,
            message=f"Data written successfully to shard {shard_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/read/{key}", response_model=ReadResponse)
async def read_data(key: str):
    """
    Read data with cache and sharding:
    1. Try cache first
    2. If miss, determine shard and read from it
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
                shard_id=cached_data.get('shard_id')
            )

        # Cache miss - determine shard and read
        shard_id = get_shard_id(key)

        with get_shard_connection(shard_id) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT key, value, created_at, updated_at
                    FROM records
                    WHERE key = %s
                """, (key,))
                result = cur.fetchone()

        if result:
            # Add shard_id to the result
            result_dict = dict(result)
            result_dict['shard_id'] = shard_id

            # Store in cache for future reads
            set_in_cache(key, result_dict)

            return ReadResponse(
                success=True,
                key=result['key'],
                value=result['value'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                from_cache=False,
                shard_id=shard_id
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found",
                from_cache=False,
                shard_id=shard_id
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get combined cache, pool, and sharding statistics"""
    try:
        cache_stats = get_cache_stats()

        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0

        # Get pool sizes for each shard
        shard_pool_sizes = {}
        for shard_id in range(settings.num_shards):
            pool = get_shard_pool(shard_id)
            shard_pool_sizes[f"shard_{shard_id}"] = getattr(pool, 'min_size', 0) if pool else 0

        # Get shard distribution
        shard_distribution = get_shard_stats()

        return StatsResponse(
            cache_available=cache_stats.get("available", False),
            cache_hits=hits if cache_stats.get("available") else None,
            cache_misses=misses if cache_stats.get("available") else None,
            cache_keys=cache_stats.get("keys", 0) if cache_stats.get("available") else None,
            cache_hit_rate=round(hit_rate, 2) if cache_stats.get("available") else None,
            num_shards=settings.num_shards,
            shard_pool_sizes=shard_pool_sizes,
            shard_distribution=shard_distribution
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check all shards
        shard_health = {}
        for shard_id in range(settings.num_shards):
            try:
                with get_shard_connection(shard_id) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                shard_health[f"shard_{shard_id}"] = "healthy"
            except Exception:
                shard_health[f"shard_{shard_id}"] = "unhealthy"

        # Check Redis
        cache_available = get_cache_stats().get("available", False)

        return {
            "status": "healthy",
            "layer": "4-db-sharding",
            "shards": shard_health,
            "cache": "healthy" if cache_available else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
