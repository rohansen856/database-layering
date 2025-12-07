"""MongoDB for flexible schema documents"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from app.config import settings

client = None
db = None
collection = None

def init_mongodb():
    """Initialize MongoDB connection"""
    global client, db, collection
    try:
        client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        db = client['polyglot_db']
        collection = db['documents']
        print("MongoDB connected")
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")
        raise

def close_mongodb():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("MongoDB connection closed")

def get_collection():
    """Get MongoDB collection"""
    if collection is None:
        raise ValueError("MongoDB not initialized")
    return collection

def write_document(key: str, data: dict) -> bool:
    """Write or update a document in MongoDB"""
    col = get_collection()
    result = col.update_one(
        {'key': key},
        {'$set': {'key': key, 'data': data}},
        upsert=True
    )
    return result.acknowledged

def read_document(key: str) -> dict:
    """Read a document from MongoDB"""
    col = get_collection()
    doc = col.find_one({'key': key})
    return doc

def get_document_count() -> int:
    """Get total number of documents"""
    col = get_collection()
    return col.count_documents({})

def get_connection_count() -> int:
    """Get number of active MongoDB connections"""
    if client:
        # This is an approximation
        return 1  # Single client connection
    return 0
