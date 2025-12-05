from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Command Models (Write)
class WriteCommand(BaseModel):
    key: str
    value: str

class WriteResponse(BaseModel):
    success: bool
    key: str
    event_id: Optional[str] = None
    message: Optional[str] = None

# Query Models (Read)
class ReadQuery(BaseModel):
    key: str

class ReadResponse(BaseModel):
    success: bool
    key: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    read_count: Optional[int] = None  # Denormalized field
    message: Optional[str] = None
    from_read_db: bool = True

class StatsResponse(BaseModel):
    write_db_pool_size: int
    read_db_pool_size: int
    events_published: int
    events_projected: int
    read_db_records: int
    write_db_records: int
