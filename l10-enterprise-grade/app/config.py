from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # Database Shards
    db_shard1_url: str = "postgresql://dbuser:dbpassword@localhost:5453/enterprise_db"
    db_shard2_url: str = "postgresql://dbuser:dbpassword@localhost:5454/enterprise_db"

    # Caches
    cache_l1_url: str = "redis://localhost:6390"
    cache_l2_url: str = "redis://localhost:6391"

    # Rate Limiter
    rate_limiter_url: str = "redis://localhost:6392"

    # Connection Pool
    db_pool_min_size: int = 2
    db_pool_max_size: int = 20

    # Cache Configuration
    cache_ttl: int = 300

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 30  # seconds

    # Authentication
    auth_enabled: bool = True
    api_key: str = "enterprise-api-key-demo"

    # Application
    environment: str = "production"
    log_level: str = "INFO"
    enable_metrics: bool = True
    prometheus_port: int = 8001

    model_config = ConfigDict(env_file=".env")

settings = Settings()

# Shard Configuration
SHARDS = {
    "shard1": settings.db_shard1_url,
    "shard2": settings.db_shard2_url
}
