from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # US-EAST Region
    db_us_east_url: str = "postgresql://dbuser:dbpassword@localhost:5450/global_db"
    cache_us_east_url: str = "redis://localhost:6387"

    # EU-WEST Region
    db_eu_west_url: str = "postgresql://dbuser:dbpassword@localhost:5451/global_db"
    cache_eu_west_url: str = "redis://localhost:6388"

    # ASIA-PAC Region
    db_asia_pac_url: str = "postgresql://dbuser:dbpassword@localhost:5452/global_db"
    cache_asia_pac_url: str = "redis://localhost:6389"

    # Configuration
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    replication_enabled: bool = True
    cache_ttl: int = 300

    model_config = ConfigDict(env_file=".env")

settings = Settings()

# Region mapping
REGIONS = {
    "us-east": {
        "db_url": settings.db_us_east_url,
        "cache_url": settings.cache_us_east_url,
        "name": "US-EAST"
    },
    "eu-west": {
        "db_url": settings.db_eu_west_url,
        "cache_url": settings.cache_eu_west_url,
        "name": "EU-WEST"
    },
    "asia-pac": {
        "db_url": settings.db_asia_pac_url,
        "cache_url": settings.cache_asia_pac_url,
        "name": "ASIA-PAC"
    }
}
