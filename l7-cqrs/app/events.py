import redis
import json
from app.config import settings
from typing import Optional, List, Dict
from datetime import datetime

redis_client = None
events_published = 0
events_projected = 0

def init_event_store():
    """Initialize Redis for event streaming"""
    global redis_client
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        print("Event store (Redis Streams) connected")
    except Exception as e:
        print(f"Event store connection failed: {e}")
        redis_client = None

def close_event_store():
    """Close event store connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None

def publish_event(event_type: str, data: Dict) -> Optional[str]:
    """Publish an event to the stream"""
    global events_published
    
    if not redis_client:
        return None
    
    try:
        event = {
            "type": event_type,
            "timestamp": str(datetime.utcnow()),
            "data": json.dumps(data)
        }
        
        # Add to Redis Stream
        event_id = redis_client.xadd(settings.event_stream_name, event)
        events_published += 1
        return event_id
    except Exception as e:
        print(f"Error publishing event: {e}")
        return None

def read_events(last_id: str = "0", count: int = 10) -> List[tuple]:
    """Read events from the stream"""
    if not redis_client:
        return []
    
    try:
        # Read from stream
        events = redis_client.xread(
            {settings.event_stream_name: last_id},
            count=count,
            block=1000  # Block for 1 second
        )
        
        if events:
            return events[0][1]  # Return list of (event_id, event_data)
        return []
    except Exception as e:
        print(f"Error reading events: {e}")
        return []

def mark_event_processed():
    """Mark that an event has been processed"""
    global events_projected
    events_projected += 1
    # Also store in Redis so API can read it
    if redis_client:
        try:
            redis_client.incr("events_projected_count")
        except:
            pass

def get_event_stats() -> Dict:
    """Get event statistics"""
    stream_length = 0
    projected_count = events_projected  # Local count

    if redis_client:
        try:
            info = redis_client.xinfo_stream(settings.event_stream_name)
            stream_length = info.get('length', 0)
            # Get projection count from Redis (set by projector process)
            redis_projected = redis_client.get("events_projected_count")
            if redis_projected:
                projected_count = int(redis_projected)
        except:
            pass

    return {
        "events_published": events_published,
        "events_projected": projected_count,
        "stream_length": stream_length
    }
