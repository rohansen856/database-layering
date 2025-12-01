from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbuser:dbpassword@localhost:5445/appdb"
    redis_url: str = "redis://localhost:6382"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    l1_cache_size: int = 100  # Max items in L1 cache
    l1_cache_ttl: int = 60    # L1 cache TTL in seconds
    l2_cache_ttl: int = 300   # L2 (Redis) cache TTL in seconds

    class Config:
        env_file = ".env"

settings = Settings()
