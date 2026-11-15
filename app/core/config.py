"""Configuration from environment only. No secrets are hardcoded here.

See the repository-root .env.example for the placeholder values.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Nexora"
    app_env: str = "development"
    debug: bool = False

    database_url: str = "sqlite:///./nexora.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    jwt_secret: str = "CHANGE_ME_GENERATE_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "nexora"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    cors_origins: str = "http://localhost:3000,http://localhost:8000"


settings = Settings()
