from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.models import (
    TransactionWrite, TransactionResponse,
    DocumentWrite, DocumentResponse,
    ReadResponse, StatsResponse
)
from app.postgres_db import (
    init_pool, close_pool, init_schema,
    write_transaction, get_user_transactions, get_transaction_count, get_pool
)
from app.mongodb import (
    init_mongodb, close_mongodb,
    write_document, read_document, get_document_count, get_connection_count
)
from app.cache import (
    init_cache, close_cache,
    cache_set, cache_get, cache_delete, cache_keys_count
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    init_pool()
    init_mongodb()
    init_cache()
    init_schema()
    print("Layer 8 - Polyglot Persistence API started")

    yield

    # Shutdown
    close_pool()
    close_mongodb()
    close_cache()
    print("Layer 8 - Polyglot Persistence API stopped")

app = FastAPI(title="Layer 8 - Polyglot Persistence", lifespan=lifespan)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "layer": "8-polyglot-persistence",
        "databases": ["PostgreSQL", "MongoDB", "Redis"]
    }

@app.post("/write/transaction", response_model=TransactionResponse)
async def write_transaction_endpoint(transaction: TransactionWrite):
    """
    Write transactional data to PostgreSQL (ACID compliance)
    Use for: Financial transactions, orders, critical data
    """
    try:
        transaction_id = write_transaction(
            transaction.user_id,
            transaction.amount,
            transaction.transaction_type
        )

        return TransactionResponse(
            success=True,
            transaction_id=transaction_id,
            message="Transaction written to PostgreSQL",
            stored_in="PostgreSQL"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/write/document", response_model=DocumentResponse)
async def write_document_endpoint(document: DocumentWrite):
    """
    Write flexible document to MongoDB
    Use for: User profiles, product catalogs, flexible schemas
    """
    try:
        # Write to MongoDB
        success = write_document(document.key, document.data)

        # Invalidate cache
        cache_delete(f"doc:{document.key}")

        return DocumentResponse(
            success=success,
            key=document.key,
            data=document.data,
            from_cache=False,
            stored_in="MongoDB"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/transaction/{user_id}", response_model=ReadResponse)
async def read_transactions(user_id: str):
    """
    Read transactional data from PostgreSQL
    Returns all transactions for a user
    """
    try:
        # Check cache first
        cache_key = f"transactions:{user_id}"
        cached = cache_get(cache_key)

        if cached:
            return ReadResponse(
                success=True,
                key=user_id,
                value=cached,
                source="cache"
            )

        # Read from PostgreSQL
        transactions = get_user_transactions(user_id)

        if transactions:
            # Convert to dict format
            trans_list = [
                {
                    "id": t[0],
                    "user_id": t[1],
                    "amount": float(t[2]),
                    "transaction_type": t[3],
                    "created_at": t[4].isoformat() if t[4] else None
                }
                for t in transactions
            ]

            # Cache result
            cache_set(cache_key, trans_list, 60)  # Short TTL for transactional data

            return ReadResponse(
                success=True,
                key=user_id,
                value=trans_list,
                source="postgres"
            )
        else:
            return ReadResponse(
                success=False,
                key=user_id,
                source="postgres",
                message="No transactions found"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/document/{key}", response_model=DocumentResponse)
async def read_document_endpoint(key: str):
    """
    Read document from MongoDB (with Redis caching)
    Cache-aside pattern for flexible schema data
    """
    try:
        # Check cache first
        cache_key = f"doc:{key}"
        cached = cache_get(cache_key)

        if cached:
            return DocumentResponse(
                success=True,
                key=key,
                data=cached,
                from_cache=True,
                stored_in="Redis (cache)"
            )

        # Read from MongoDB
        doc = read_document(key)

        if doc:
            # Cache the result
            cache_set(cache_key, doc['data'])

            return DocumentResponse(
                success=True,
                key=key,
                data=doc['data'],
                from_cache=False,
                stored_in="MongoDB"
            )
        else:
            return DocumentResponse(
                success=False,
                key=key,
                stored_in="MongoDB",
                data={"message": "Document not found"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about all database systems"""
    try:
        pool = get_pool()
        pool_stats = pool.get_stats() if pool else {}

        return StatsResponse(
            postgres_pool_size=pool_stats.get('pool_size', 0),
            mongodb_connections=get_connection_count(),
            cache_keys=cache_keys_count(),
            total_transactions=get_transaction_count(),
            total_documents=get_document_count()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
