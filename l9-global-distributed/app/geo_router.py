"""Geo-routing logic for region selection"""
import random
from typing import Optional

# Simulated geo-location mapping based on client IP or explicit region header
# In production, this would use actual GeoIP databases or client headers

def get_region_from_header(region_header: Optional[str]) -> str:
    """
    Get region from explicit header or default to nearest region
    In production: Use GeoIP database to determine closest region
    """
    if region_header and region_header in ["us-east", "eu-west", "asia-pac"]:
        return region_header

    # Default to us-east for demo purposes
    # In production: Use client IP geolocation
    return "us-east"

def get_optimal_read_region(key: str, user_region: str) -> str:
    """
    Determine optimal read region based on data locality and user location
    Strategy: Read from user's region first (lowest latency)
    """
    return user_region

def get_write_region(user_region: str) -> str:
    """
    Determine primary write region
    Strategy: Write to user's nearest region first
    """
    return user_region

def get_replication_regions(primary_region: str) -> list:
    """
    Get list of regions to replicate to (all regions except primary)
    """
    all_regions = ["us-east", "eu-west", "asia-pac"]
    return [r for r in all_regions if r != primary_region]
