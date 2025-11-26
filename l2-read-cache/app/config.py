from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbuser:dbpassword@localhost:5434/appdb"
    redis_url: str = "redis://localhost:6379"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    cache_ttl: int = 300  # 5 minutes

    class Config:
        env_file = ".env"

settings = Settings()
