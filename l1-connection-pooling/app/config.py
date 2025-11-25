from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbuser:dbpassword@localhost:5433/appdb"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
