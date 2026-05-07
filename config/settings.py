from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Aplikasi
    secret_key: str = "change-me-in-production"
    debug: bool = False

    # Cache
    cache_backend: str = "memory"
    redis_url: str | None = None
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # Penjadwal
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Asia/Jakarta"

    # Basis data
    namedb: str = "aodproject"
    userdb: str = "aoduser"
    passdb: str = "changeme"
    dbhost: str = "db"
    dbport: str = "5432"

    # API key eksternal
    api_key: str = ""
    userhimawari: str = ""
    passhimawari: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.userdb}:{self.passdb}"
            f"@{self.dbhost}:{self.dbport}/{self.namedb}"
        )


settings = Settings()
