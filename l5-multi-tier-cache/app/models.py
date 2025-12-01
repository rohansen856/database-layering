from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WriteRequest(BaseModel):
    key: str
    value: str

class WriteResponse(BaseModel):
    success: bool
    key: str
    message: Optional[str] = None

class ReadResponse(BaseModel):
    success: bool
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message: Optional[str] = None
    cache_level: Optional[str] = None  # "L1", "L2", or "L3" (database)

class StatsResponse(BaseModel):
    l1_cache_available: bool
    l1_cache_size: Optional[int] = None
    l1_cache_max_size: Optional[int] = None
    l1_cache_hits: Optional[int] = None
    l1_cache_misses: Optional[int] = None
    l1_hit_rate: Optional[float] = None
    l2_cache_available: bool
    l2_cache_keys: Optional[int] = None
    l2_cache_hits: Optional[int] = None
    l2_cache_misses: Optional[int] = None
    l2_hit_rate: Optional[float] = None
    db_pool_size: int
    total_hits: Optional[int] = None
    total_misses: Optional[int] = None
    overall_hit_rate: Optional[float] = None
