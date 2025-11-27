from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WriteRequest(BaseModel):
    key: str
    value: str

class WriteResponse(BaseModel):
    success: bool
    key: str
    message: str

class ReadResponse(BaseModel):
    success: bool
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message: Optional[str] = None
    from_cache: Optional[bool] = False
    from_replica: Optional[bool] = False

class StatsResponse(BaseModel):
    cache_available: bool
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_keys: Optional[int] = None
    cache_hit_rate: Optional[float] = None
    primary_pool_size: Optional[int] = None
    replica_pool_size: Optional[int] = None
