from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api/v1"
    POSTGRES_DSN: str = "postgresql+psycopg://portfolio:portfolio@localhost:8031/portfolio_lab"
    REDIS_URL: str = "redis://localhost:8033/0"
    DATASET_VERSION: str = "current"
    CACHE_DEFAULT_TTL_SECONDS: int = 604800

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
