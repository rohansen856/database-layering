from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WriteRequest(BaseModel):
    key: str
    value: str

class WriteResponse(BaseModel):
    success: bool
    key: str
    shard_id: Optional[int] = None
    message: Optional[str] = None

class ReadResponse(BaseModel):
    success: bool
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message: Optional[str] = None
    from_cache: bool = False
    shard_id: Optional[int] = None

class StatsResponse(BaseModel):
    cache_available: bool
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_keys: Optional[int] = None
    cache_hit_rate: Optional[float] = None
    num_shards: int
    shard_pool_sizes: dict
    shard_distribution: Optional[dict] = None
