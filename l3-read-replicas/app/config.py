from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    primary_database_url: str = "postgresql://dbuser:dbpassword@localhost:5435/appdb"
    replica_database_url: str = "postgresql://dbuser:dbpassword@localhost:5436/appdb"
    redis_url: str = "redis://localhost:6380"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    cache_ttl: int = 300  # 5 minutes

    class Config:
        env_file = ".env"

settings = Settings()
