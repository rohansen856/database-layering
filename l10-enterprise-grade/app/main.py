from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
from typing import Optional
import time
from app.models import (
    WriteRequest, WriteResponse,
    ReadResponse, HealthResponse, MetricsResponse
)
from app.config import settings, SHARDS
from app.database import (
    init_pools, close_pools,
    write_record, read_record, get_shard_for_key,
    get_shard_stats, is_shard_healthy
)
from app.cache import (
    init_caches, close_caches,
    cache_get, cache_set, cache_delete,
    get_cache_stats, is_cache_healthy
)
from app.rate_limiter import (
    init_rate_limiter, close_rate_limiter,
    is_rate_limited
)
from app.circuit_breaker import get_all_states
from app.metrics import (
    http_requests_total, http_request_duration,
    rate_limit_exceeded_total, get_metrics, get_content_type,
    Timer
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    init_pools()
    init_caches()
    init_rate_limiter()
    print(f"Layer 10 - Enterprise-Grade API started ({settings.environment})")

    yield

    # Shutdown
    close_pools()
    close_caches()
    close_rate_limiter()
    print("Layer 10 - Enterprise-Grade API stopped")

app = FastAPI(
    title="Layer 10 - Enterprise-Grade",
    description="Full-stack enterprise database architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware for authentication
async def verify_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    """Verify API key if authentication is enabled"""
    if not settings.auth_enabled:
        return True

    if x_api_key != settings.api_key:
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status="401"
        ).inc()
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Middleware for rate limiting
async def check_rate_limit(request: Request, x_client_id: Optional[str] = Header("default")):
    """Check rate limit for client"""
    is_limited, remaining, reset_in = is_rate_limited(x_client_id)

    if is_limited:
        rate_limit_exceeded_total.inc()
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status="429"
        ).inc()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {reset_in} seconds"
        )

    # Add rate limit headers to response
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = reset_in

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check with comprehensive system status"""
    shards_health = {shard: is_shard_healthy(shard) for shard in SHARDS.keys()}
    caches_health = {
        "L1": is_cache_healthy("L1"),
        "L2": is_cache_healthy("L2")
    }

    rate_limiter_healthy = True
    try:
        is_rate_limited("health_check")
    except:
        rate_limiter_healthy = False

    return HealthResponse(
        status="healthy" if all(shards_health.values()) else "degraded",
        layer="10-enterprise-grade",
        environment=settings.environment,
        shards_healthy=shards_health,
        caches_healthy=caches_health,
        rate_limiter_healthy=rate_limiter_healthy,
        circuit_breakers=get_all_states()
    )

@app.post("/write", response_model=WriteResponse, dependencies=[])
async def write(
    request: WriteRequest,
    api_request: Request,
    x_api_key: Optional[str] = Header(None),
    x_client_id: Optional[str] = Header("default")
):
    """Write with auth, rate limiting, sharding, and caching"""
    # Verify auth
    await verify_api_key(api_request, x_api_key)

    # Check rate limit
    await check_rate_limit(api_request, x_client_id)

    start_time = time.time()

    try:
        # Write to database (with automatic sharding)
        shard = write_record(request.key, request.value)

        # Invalidate cache
        cache_delete(request.key)

        # Set in cache
        cache_set(request.key, request.value)

        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method="POST",
            endpoint="/write",
            status="200"
        ).inc()
        http_request_duration.labels(
            method="POST",
            endpoint="/write"
        ).observe(duration)

        return WriteResponse(
            success=True,
            key=request.key,
            shard=shard,
            cached=True,
            message=f"Written to {shard} and cached"
        )
    except Exception as e:
        http_requests_total.labels(
            method="POST",
            endpoint="/write",
            status="500"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/{key}", response_model=ReadResponse)
async def read(
    key: str,
    api_request: Request,
    x_api_key: Optional[str] = Header(None),
    x_client_id: Optional[str] = Header("default")
):
    """Read with auth, rate limiting, multi-tier caching"""
    # Verify auth
    await verify_api_key(api_request, x_api_key)

    # Check rate limit
    await check_rate_limit(api_request, x_client_id)

    start_time = time.time()

    try:
        # Try cache first (L1 -> L2)
        value, cache_level = cache_get(key)

        if value:
            duration = time.time() - start_time
            http_requests_total.labels(
                method="GET",
                endpoint="/read",
                status="200"
            ).inc()
            http_request_duration.labels(
                method="GET",
                endpoint="/read"
            ).observe(duration)

            return ReadResponse(
                success=True,
                key=key,
                value=value,
                cache_hit=True,
                cache_level=cache_level,
                latency_ms=round(duration * 1000, 2)
            )

        # Cache miss - read from database
        shard = get_shard_for_key(key)
        value = read_record(shard, key)

        if value:
            # Cache the result
            cache_set(key, value)

            duration = time.time() - start_time
            http_requests_total.labels(
                method="GET",
                endpoint="/read",
                status="200"
            ).inc()
            http_request_duration.labels(
                method="GET",
                endpoint="/read"
            ).observe(duration)

            return ReadResponse(
                success=True,
                key=key,
                value=value,
                cache_hit=False,
                shard=shard,
                latency_ms=round(duration * 1000, 2)
            )

        # Not found
        http_requests_total.labels(
            method="GET",
            endpoint="/read",
            status="404"
        ).inc()

        return ReadResponse(
            success=False,
            key=key,
            cache_hit=False,
            message="Key not found"
        )
    except Exception as e:
        http_requests_total.labels(
            method="GET",
            endpoint="/read",
            status="500"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    return Response(content=get_metrics(), media_type=get_content_type())

@app.get("/stats")
async def stats():
    """Internal statistics"""
    cache_stats = get_cache_stats()
    shard_stats = {shard: get_shard_stats(shard) for shard in SHARDS.keys()}

    return {
        "environment": settings.environment,
        "shards": shard_stats,
        "cache": cache_stats,
        "circuit_breakers": get_all_states(),
        "rate_limiting": {
            "enabled": True,
            "max_requests": settings.rate_limit_requests,
            "window_seconds": settings.rate_limit_window
        },
        "features": {
            "authentication": settings.auth_enabled,
            "metrics": settings.enable_metrics,
            "circuit_breakers": True,
            "rate_limiting": True,
            "multi_tier_cache": True,
            "database_sharding": True
        }
    }
