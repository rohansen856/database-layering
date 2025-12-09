from fastapi import FastAPI, HTTPException, Header
from contextlib import asynccontextmanager
from typing import Optional
import time
from app.models import (
    WriteRequest, WriteResponse,
    ReadResponse, RegionStats, GlobalStats
)
from app.config import REGIONS, settings
from app.regional_db import (
    init_all_regions, close_all_regions,
    write_record, read_record,
    get_record_count, get_cache_keys_count,
    get_pool_stats, is_region_healthy
)
from app.geo_router import (
    get_region_from_header,
    get_optimal_read_region,
    get_write_region,
    get_replication_regions
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    init_all_regions()
    print("Layer 9 - Global Distributed DB API started")

    yield

    # Shutdown
    close_all_regions()
    print("Layer 9 - Global Distributed DB API stopped")

app = FastAPI(title="Layer 9 - Global Distributed DB", lifespan=lifespan)

@app.get("/health")
async def health():
    """Health check endpoint"""
    region_health = {region: is_region_healthy(region) for region in REGIONS.keys()}

    return {
        "status": "healthy",
        "layer": "9-global-distributed",
        "regions": region_health,
        "total_regions": len(REGIONS),
        "healthy_regions": sum(region_health.values())
    }

@app.post("/write", response_model=WriteResponse)
async def write_data(
    request: WriteRequest,
    x_region: Optional[str] = Header(None, alias="X-Region")
):
    """
    Write data with global replication
    - Writes to primary region (based on geo-routing)
    - Asynchronously replicates to other regions
    """
    try:
        # Determine write region
        user_region = get_region_from_header(x_region or request.region)
        primary_region = get_write_region(user_region)

        # Write to primary region
        write_record(primary_region, request.key, request.value)

        # Replicate to other regions if enabled
        replicated_regions = []
        if settings.replication_enabled:
            replication_targets = get_replication_regions(primary_region)
            for target_region in replication_targets:
                try:
                    write_record(target_region, request.key, request.value)
                    replicated_regions.append(REGIONS[target_region]["name"])
                except Exception as e:
                    print(f"Replication to {target_region} failed: {e}")

        return WriteResponse(
            success=True,
            key=request.key,
            primary_region=REGIONS[primary_region]["name"],
            replicated_to=replicated_regions,
            message=f"Written to {REGIONS[primary_region]['name']}" +
                    (f" and replicated to {len(replicated_regions)} regions" if replicated_regions else "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read/{key}", response_model=ReadResponse)
async def read_data(
    key: str,
    x_region: Optional[str] = Header(None, alias="X-Region")
):
    """
    Read data with geo-routing
    - Reads from nearest region (lowest latency)
    - Falls back to other regions if primary unavailable
    """
    try:
        # Determine optimal read region
        user_region = get_region_from_header(x_region)
        read_region = get_optimal_read_region(key, user_region)

        start_time = time.time()

        # Try primary region
        value, source = read_record(read_region, key)

        if value is not None:
            latency_ms = (time.time() - start_time) * 1000
            return ReadResponse(
                success=True,
                key=key,
                value=value,
                source=source,
                region=REGIONS[read_region]["name"],
                latency_ms=round(latency_ms, 2)
            )

        # If not found, try other regions (disaster recovery)
        for fallback_region in REGIONS.keys():
            if fallback_region != read_region:
                try:
                    value, source = read_record(fallback_region, key)
                    if value is not None:
                        latency_ms = (time.time() - start_time) * 1000
                        return ReadResponse(
                            success=True,
                            key=key,
                            value=value,
                            source=source,
                            region=f"{REGIONS[fallback_region]['name']} (fallback)",
                            latency_ms=round(latency_ms, 2)
                        )
                except:
                    continue

        # Not found in any region
        return ReadResponse(
            success=False,
            key=key,
            source="none",
            region=REGIONS[read_region]["name"],
            message="Key not found in any region"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=GlobalStats)
async def get_global_stats():
    """Get statistics across all regions"""
    try:
        region_stats = []
        total_records = 0

        for region_key, region_config in REGIONS.items():
            try:
                pool_stats = get_pool_stats(region_key)
                record_count = get_record_count(region_key)
                cache_keys = get_cache_keys_count(region_key)
                healthy = is_region_healthy(region_key)

                region_stats.append(RegionStats(
                    region=region_config["name"],
                    db_pool_size=pool_stats.get('pool_size', 0),
                    cache_keys=cache_keys,
                    total_records=record_count,
                    healthy=healthy
                ))
                total_records += record_count
            except Exception as e:
                print(f"Error getting stats for {region_key}: {e}")
                region_stats.append(RegionStats(
                    region=region_config["name"],
                    db_pool_size=0,
                    cache_keys=0,
                    total_records=0,
                    healthy=False
                ))

        healthy_count = sum(1 for rs in region_stats if rs.healthy)

        return GlobalStats(
            regions=region_stats,
            total_regions=len(REGIONS),
            healthy_regions=healthy_count,
            total_records_global=total_records,
            replication_enabled=settings.replication_enabled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/regions")
async def list_regions():
    """List all available regions"""
    return {
        "regions": [
            {
                "key": key,
                "name": config["name"],
                "healthy": is_region_healthy(key)
            }
            for key, config in REGIONS.items()
        ]
    }
