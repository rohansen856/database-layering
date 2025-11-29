from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    shard_0_url: str = "postgresql://dbuser:dbpassword@localhost:5440/appdb_shard_0"
    shard_1_url: str = "postgresql://dbuser:dbpassword@localhost:5441/appdb_shard_1"
    shard_2_url: str = "postgresql://dbuser:dbpassword@localhost:5442/appdb_shard_2"
    redis_url: str = "redis://localhost:6381"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    cache_ttl: int = 300  # 5 minutes
    num_shards: int = 3

    class Config:
        env_file = ".env"

settings = Settings()
