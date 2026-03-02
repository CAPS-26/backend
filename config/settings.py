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

    # Database
    namedb: str = "aodproject"
    userdb: str = "aoduser"
    passdb: str = "changeme"
    dbhost: str = "localhost"
    dbport: str = "5432"

    # API key eksternal
    api_key: str = ""
    userhimawari: str = ""
    passhimawari: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.userdb}:{self.passdb}"
            f"@{self.dbhost}:{self.dbport}/{self.namedb}"
        )


settings = Settings()
