from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "DukonPro API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    secret_key: str = Field(min_length=16)
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    backend_cors_origins: str = "http://localhost:3000,http://localhost:5173"

    sms_provider: Literal["fake", "eskiz"] = "fake"
    eskiz_base_url: str = "https://notify.eskiz.uz/api"
    eskiz_email: str | None = None
    eskiz_password: str | None = None
    eskiz_from: str = "4546"

    otp_code_ttl_seconds: int = 300
    otp_verification_token_ttl_seconds: int = 600
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        value = (value.strip() or "/api/v1").replace("\\", "/")
        api_marker = "/api/"
        if ":/" in value and api_marker in value:
            value = value[value.index(api_marker) :]
        return value if value.startswith("/") else f"/{value}"

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
