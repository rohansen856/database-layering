"""
Background worker that processes queued writes.
Run with: python -m app.worker
"""
import time
import signal
import sys
from app.config import settings
from app.database import init_pool, close_pool, get_db_connection, init_db
from app.queue import init_queue, close_queue, dequeue_writes
from app.cache import invalidate_cache

running = True

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global running
    print("\nShutdown signal received, finishing current batch...")
    running = False

def process_writes(writes):
    """Process a batch of writes to the database"""
    if not writes:
        return 0

    processed = 0
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for write in writes:
                    key = write["key"]
                    value = write["value"]

                    cur.execute("""
                        INSERT INTO records (key, value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (key, value))

                    # Invalidate cache for this key
                    invalidate_cache(key)
                    processed += 1

                conn.commit()
                print(f"Processed {processed} writes")
    except Exception as e:
        print(f"Error processing writes: {e}")
        # In production, you might want to re-queue failed writes

    return processed

def main():
    """Main worker loop"""
    global running

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Initializing worker...")
    init_pool()
    init_queue()
    init_db()

    print(f"Worker started. Polling every {settings.worker_poll_interval}s...")
    print(f"Batch size: {settings.worker_batch_size}")

    try:
        while running:
            # Dequeue and process writes
            writes = dequeue_writes(batch_size=settings.worker_batch_size)

            if writes:
                process_writes(writes)
            else:
                # No writes to process, sleep
                time.sleep(settings.worker_poll_interval)

    finally:
        print("Shutting down worker...")
        close_pool()
        close_queue()
        print("Worker stopped")

if __name__ == "__main__":
    main()
