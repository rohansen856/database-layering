from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbuser:dbpassword@localhost:5432/appdb"

    class Config:
        env_file = ".env"

settings = Settings()
