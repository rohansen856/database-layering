"""
Projector: Projects events from write DB to read DB.
This creates the read model optimized for queries.
Run with: python -m app.projector
"""
import time
import signal
import sys
import json
from app.config import settings
from app.database import init_pools, close_pools, get_read_connection, init_write_db, init_read_db
from app.events import init_event_store, close_event_store, read_events, mark_event_processed

running = True
last_event_id = "0"

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global running
    print("\nShutdown signal received...")
    running = False

def project_event(event_id, event_data):
    """Project an event to the read database"""
    try:
        # Redis client has decode_responses=True, so data is already strings
        event_type = event_data.get('type', '')
        data = json.loads(event_data.get('data', '{}'))
        
        if event_type == "RecordCreated" or event_type == "RecordUpdated":
            key = data.get("key")
            value = data.get("value")
            
            with get_read_connection() as conn:
                with conn.cursor() as cur:
                    # Upsert into read database with denormalized data
                    cur.execute("""
                        INSERT INTO records (key, value, created_at, updated_at, write_count)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                        ON CONFLICT (key)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = CURRENT_TIMESTAMP,
                            write_count = records.write_count + 1
                    """, (key, value))
                    conn.commit()
            
            mark_event_processed()
            print(f"Projected event {event_id}: {event_type} for key={key}")
            return True
    except Exception as e:
        print(f"Error projecting event {event_id}: {e}")
        return False

def main():
    """Main projector loop"""
    global running, last_event_id
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Initializing projector...")
    init_pools()
    init_event_store()
    init_write_db()
    init_read_db()
    
    print(f"Projector started. Polling every {settings.projector_poll_interval}s...")
    
    try:
        while running:
            # Read events from stream
            events = read_events(last_id=last_event_id, count=settings.projector_batch_size)
            
            if events:
                for event_id, event_data in events:
                    project_event(event_id, event_data)
                    # event_id is already a string (decode_responses=True)
                    last_event_id = event_id
            else:
                # No events, sleep
                time.sleep(settings.projector_poll_interval)
    
    finally:
        print("Shutting down projector...")
        close_pools()
        close_event_store()
        print("Projector stopped")

if __name__ == "__main__":
    main()
