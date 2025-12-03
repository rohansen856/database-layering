from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WriteRequest(BaseModel):
    key: str
    value: str

class WriteResponse(BaseModel):
    success: bool
    key: str
    queued: bool = False
    message: Optional[str] = None

class ReadResponse(BaseModel):
    success: bool
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message: Optional[str] = None
    from_cache: bool = False

class StatsResponse(BaseModel):
    cache_available: bool
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_keys: Optional[int] = None
    cache_hit_rate: Optional[float] = None
    db_pool_size: int
    queue_length: int
    writes_queued: int
    writes_processed: int
