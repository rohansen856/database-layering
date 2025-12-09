from pydantic import BaseModel
from typing import Optional, List

class WriteRequest(BaseModel):
    """Write request model"""
    key: str
    value: str
    region: Optional[str] = None  # If None, geo-router decides

class WriteResponse(BaseModel):
    """Write response model"""
    success: bool
    key: str
    primary_region: str
    replicated_to: List[str]
    message: str

class ReadResponse(BaseModel):
    """Read response model"""
    success: bool
    key: str
    value: Optional[str] = None
    source: str  # "cache" or "database"
    region: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None

class RegionStats(BaseModel):
    """Stats for a single region"""
    region: str
    db_pool_size: int
    cache_keys: int
    total_records: int
    healthy: bool

class GlobalStats(BaseModel):
    """Global statistics across all regions"""
    regions: List[RegionStats]
    total_regions: int
    healthy_regions: int
    total_records_global: int
    replication_enabled: bool
