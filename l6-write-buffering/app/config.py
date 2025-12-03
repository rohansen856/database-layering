from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbuser:dbpassword@localhost:5446/appdb"
    redis_url: str = "redis://localhost:6383"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    cache_ttl: int = 300  # 5 minutes
    write_queue_name: str = "write_queue"
    worker_enabled: bool = False
    worker_batch_size: int = 10
    worker_poll_interval: int = 1  # seconds

    class Config:
        env_file = ".env"

settings = Settings()
