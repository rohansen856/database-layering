import redis
import json
from app.config import settings
from typing import Optional, List, Dict

redis_client = None
writes_queued = 0
writes_processed = 0

def init_queue():
    """Initialize queue (uses same Redis as cache)"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=False  # Use bytes for queue to handle JSON properly
        )
        redis_client.ping()
        print("Queue (Redis) connected successfully")
    except Exception as e:
        print(f"Queue connection failed: {e}")
        redis_client = None

def close_queue():
    """Close queue connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None

def enqueue_write(key: str, value: str) -> bool:
    """Add a write operation to the queue"""
    global writes_queued

    if not redis_client:
        return False

    try:
        write_data = {
            "key": key,
            "value": value,
            "timestamp": str(__import__('datetime').datetime.utcnow())
        }

        # Push to queue (list)
        redis_client.rpush(settings.write_queue_name, json.dumps(write_data))
        writes_queued += 1
        return True
    except Exception as e:
        print(f"Queue enqueue error: {e}")
        return False

def dequeue_writes(batch_size: int = 10) -> List[Dict]:
    """Dequeue multiple write operations"""
    global writes_processed

    if not redis_client:
        return []

    try:
        # Use LPOP with count for batch processing
        writes = []
        for _ in range(batch_size):
            item = redis_client.lpop(settings.write_queue_name)
            if item is None:
                break
            writes.append(json.loads(item.decode('utf-8')))
            writes_processed += 1

        return writes
    except Exception as e:
        print(f"Queue dequeue error: {e}")
        return []

def get_queue_length() -> int:
    """Get current queue length"""
    if not redis_client:
        return 0

    try:
        return redis_client.llen(settings.write_queue_name)
    except Exception:
        return 0

def get_queue_stats() -> Dict:
    """Get queue statistics"""
    return {
        "queue_length": get_queue_length(),
        "writes_queued": writes_queued,
        "writes_processed": writes_processed
    }
