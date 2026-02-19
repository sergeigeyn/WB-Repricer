"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PriceForge"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    API_PREFIX: str = "/api"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "priceforge"
    POSTGRES_PASSWORD: str = "priceforge_dev"
    POSTGRES_DB: str = "priceforge"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # WB API
    WB_API_KEY: str = ""
    WB_API_BASE_URL: str = "https://suppliers-api.wildberries.ru"
    WB_API_MOCK_MODE: bool = True

    # AES encryption for API keys in DB
    AES_SECRET_KEY: str = "change-me-32-bytes-key-here!!!!!"

    # Seed admin user (read from .env, not from code)
    ADMIN_EMAIL: str = "admin@priceforge.ru"
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Администратор"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
