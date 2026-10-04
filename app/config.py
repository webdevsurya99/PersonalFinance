import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "FinMinimal - Personal Finance"
    APP_ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Secrets
    SECRET_KEY: str = "super-secret-key-must-be-configured-in-env-at-least-32-chars-long"
    CSRF_SECRET_KEY: str = "super-csrf-secret-key-must-be-configured-in-env-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    # Cookie settings
    SECURE_COOKIES: bool = False  # Set to True on HTTPS
    SESSION_COOKIE_NAME: str = "fin_session_token"

    # Database
    DATABASE_URL: str = "sqlite:///./finance.db"

    # Admin Defaults
    ADMIN_DEFAULT_EMAIL: str = "admin@finminimal.local"
    ADMIN_DEFAULT_PASSWORD: str = "AdminPassword123!"
    ADMIN_DEFAULT_NAME: str = "System Administrator"

    # Rate Limiting
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_GENERAL: str = "120/minute"

    # Currency
    DEFAULT_CURRENCY_SYMBOL: str = "₹"
    DEFAULT_CURRENCY_CODE: str = "INR"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
