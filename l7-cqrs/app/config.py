from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    write_db_url: str = "postgresql://dbuser:dbpassword@localhost:5447/write_db"
    read_db_url: str = "postgresql://dbuser:dbpassword@localhost:5448/read_db"
    redis_url: str = "redis://localhost:6384"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    event_stream_name: str = "events"
    projector_batch_size: int = 10
    projector_poll_interval: int = 1  # seconds

    model_config = ConfigDict(env_file=".env")

settings = Settings()
