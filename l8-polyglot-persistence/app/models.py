from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TransactionWrite(BaseModel):
    """Write model for transactional data (PostgreSQL)"""
    user_id: str
    amount: float
    transaction_type: str  # e.g., "purchase", "refund", "transfer"

class TransactionResponse(BaseModel):
    """Response model for transaction"""
    success: bool
    transaction_id: Optional[int] = None
    message: str
    stored_in: str  # Which database(s) stored the data

class DocumentWrite(BaseModel):
    """Write model for flexible document data (MongoDB)"""
    key: str
    data: Dict[str, Any]  # Flexible schema

class DocumentResponse(BaseModel):
    """Response model for document"""
    success: bool
    key: str
    data: Optional[Dict[str, Any]] = None
    from_cache: bool = False
    stored_in: str

class ReadResponse(BaseModel):
    """Generic read response"""
    success: bool
    key: str
    value: Optional[Any] = None
    source: str  # "cache", "postgres", "mongodb"
    message: Optional[str] = None

class StatsResponse(BaseModel):
    """Statistics response"""
    postgres_pool_size: int
    mongodb_connections: int
    cache_keys: int
    total_transactions: int
    total_documents: int
