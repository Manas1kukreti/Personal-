from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ExcelFlow Analytics API"
    database_url: str = "postgresql+asyncpg://excelflow:excelflow@localhost:5433/excelflow"
    upload_dir: str = "./storage/uploads"
    max_preview_rows: int = 50
    max_upload_size_mb: int = 10
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_base_url: str = "http://localhost:5173"
    default_admin_email: str = "admin@example.com"
    default_admin_password: str = "ChangeMeAdmin123"
    default_admin_name: str = "ExcelFlow Admin"
    emails_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@excelflow.local"
    smtp_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
