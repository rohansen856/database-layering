from pydantic import BaseModel
from typing import Optional, Dict, List

class WriteRequest(BaseModel):
    """Write request model"""
    key: str
    value: str

class WriteResponse(BaseModel):
    """Write response model"""
    success: bool
    key: str
    shard: str
    cached: bool
    message: str

class ReadResponse(BaseModel):
    """Read response model"""
    success: bool
    key: str
    value: Optional[str] = None
    cache_hit: bool
    cache_level: Optional[str] = None  # L1, L2, or None
    shard: Optional[str] = None
    latency_ms: Optional[float] = None
    message: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    layer: str
    environment: str
    shards_healthy: Dict[str, bool]
    caches_healthy: Dict[str, bool]
    rate_limiter_healthy: bool
    circuit_breakers: Dict[str, str]  # open, closed, half_open

class MetricsResponse(BaseModel):
    """Metrics summary response"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    cache_l1_hits: int
    cache_l2_hits: int
    cache_misses: int
    cache_hit_rate: float
    avg_latency_ms: float
    circuit_breakers_open: int

class RateLimitResponse(BaseModel):
    """Rate limit info"""
    allowed: bool
    remaining: int
    reset_in: int  # seconds
    message: str
