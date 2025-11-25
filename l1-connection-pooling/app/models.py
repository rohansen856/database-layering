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

class PoolStatsResponse(BaseModel):
    pool_size: int
    pool_available: int
    requests_waiting: int
    usage_ms: int
