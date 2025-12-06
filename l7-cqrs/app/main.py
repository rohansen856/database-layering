from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.models import WriteCommand, WriteResponse, ReadQuery, ReadResponse, StatsResponse
from app.database import (
    init_pools, close_pools,
    get_write_connection, get_read_connection,
    init_write_db, init_read_db,
    get_write_pool, get_read_pool
)
from app.events import init_event_store, close_event_store, publish_event, get_event_stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    init_pools()
    init_event_store()
    init_write_db()
    init_read_db()
    print("Layer 7 - CQRS API started")

    yield

    # Shutdown
    close_pools()
    close_event_store()
    print("Layer 7 - CQRS API stopped")

app = FastAPI(title="Layer 7 - CQRS", lifespan=lifespan)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "layer": "7-cqrs"}

@app.post("/write", response_model=WriteResponse)
async def write_command(command: WriteCommand):
    """
    Write command - writes to write database and publishes event.
    The projector will asynchronously update the read database.
    """
    try:
        # Write to write database (OLTP - normalized)
        with get_write_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO commands (key, value) VALUES (%s, %s) RETURNING id",
                    (command.key, command.value)
                )
                command_id = cur.fetchone()[0]
                conn.commit()

        # Publish event to stream
        event_id = publish_event(
            event_type="RecordCreated",
            data={"key": command.key, "value": command.value, "command_id": command_id}
        )

        return WriteResponse(
            success=True,
            key=command.key,
            event_id=event_id,
            message="Command written and event published"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/write", response_model=WriteResponse)
async def update_command(command: WriteCommand):
    """
    Update command - updates write database and publishes event.
    """
    try:
        # Write to write database
        with get_write_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO commands (key, value) VALUES (%s, %s) RETURNING id",
                    (command.key, command.value)
                )
                command_id = cur.fetchone()[0]
                conn.commit()

        # Publish update event
        event_id = publish_event(
            event_type="RecordUpdated",
            data={"key": command.key, "value": command.value, "command_id": command_id}
        )

        return WriteResponse(
            success=True,
            key=command.key,
            event_id=event_id,
            message="Command updated and event published"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/{key}", response_model=ReadResponse)
async def read_query(key: str):
    """
    Read query - reads from read database (denormalized OLAP).
    This is eventually consistent with writes.
    """
    try:
        with get_read_connection() as conn:
            with conn.cursor() as cur:
                # Update read count
                cur.execute(
                    "UPDATE records SET read_count = read_count + 1 WHERE key = %s",
                    (key,)
                )

                # Fetch record
                cur.execute(
                    "SELECT key, value, created_at, updated_at, read_count FROM records WHERE key = %s",
                    (key,)
                )
                result = cur.fetchone()
                conn.commit()

        if result:
            return ReadResponse(
                success=True,
                key=result[0],
                value=result[1],
                created_at=result[2],
                updated_at=result[3],
                read_count=result[4],
                from_read_db=True
            )
        else:
            return ReadResponse(
                success=False,
                key=key,
                message="Key not found in read database (may not be projected yet)",
                from_read_db=True
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about the CQRS system"""
    try:
        write_pool = get_write_pool()
        read_pool = get_read_pool()
        event_stats = get_event_stats()

        # Count records in both databases
        write_count = 0
        read_count = 0

        try:
            with get_write_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM commands")
                    write_count = cur.fetchone()[0]
        except:
            pass

        try:
            with get_read_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM records")
                    read_count = cur.fetchone()[0]
        except:
            pass

        return StatsResponse(
            write_db_pool_size=write_pool.get_stats()['pool_size'] if write_pool else 0,
            read_db_pool_size=read_pool.get_stats()['pool_size'] if read_pool else 0,
            events_published=event_stats['events_published'],
            events_projected=event_stats['events_projected'],
            read_db_records=read_count,
            write_db_records=write_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
