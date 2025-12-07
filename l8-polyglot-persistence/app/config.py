from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    postgres_url: str = "postgresql://dbuser:dbpassword@localhost:5449/transactional_db"
    mongodb_url: str = "mongodb://mongouser:mongopassword@localhost:27017/"
    redis_url: str = "redis://localhost:6386"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    cache_ttl: int = 300

    model_config = ConfigDict(env_file=".env")

settings = Settings()
