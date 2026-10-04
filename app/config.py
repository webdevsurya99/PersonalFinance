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

    # Storage & Persistence
    DATA_DIR: Optional[str] = None
    DATABASE_URL: Optional[str] = None

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

    @property
    def resolved_data_dir(self) -> str:
        """Determines persistent storage folder for SQLite and backups."""
        if self.DATA_DIR and os.path.exists(self.DATA_DIR):
            return self.DATA_DIR
        env_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
        if env_mount and os.path.exists(env_mount):
            return env_mount
        # Check standard cloud persistent volume paths
        for path in ["/data", "/app/data"]:
            if os.path.exists(path) and os.access(path, os.W_OK):
                return path
        return "."

    @property
    def resolved_backup_dir(self) -> str:
        """Determines backup folder location."""
        data_dir = self.resolved_data_dir
        if data_dir == ".":
            os.makedirs("backups", exist_ok=True)
            return "backups"
        backup_path = os.path.join(data_dir, "backups")
        os.makedirs(backup_path, exist_ok=True)
        return backup_path

    @property
    def resolved_database_url(self) -> str:
        """
        Resolves DATABASE_URL:
        - If PostgreSQL (e.g. Railway postgres:// or postgresql://), fixes dialect prefix.
        - If not specified, checks if a persistent volume directory exists.
        """
        db_url = self.DATABASE_URL or os.getenv("DATABASE_URL", "")
        if db_url:
            # Fix Railway postgres:// -> postgresql:// for SQLAlchemy 2.0
            if db_url.startswith("postgres://"):
                return db_url.replace("postgres://", "postgresql://", 1)
            return db_url
        
        # If no DATABASE_URL set, check if persistent /data or /app/data volume exists
        data_dir = self.resolved_data_dir
        if data_dir != ".":
            return f"sqlite:///{os.path.join(data_dir, 'finance.db')}"
        
        return "sqlite:///./finance.db"

settings = Settings()
