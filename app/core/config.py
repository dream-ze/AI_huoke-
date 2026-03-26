from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "browser_collector"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8005
    APP_ENV: str = "dev"

    BROWSER_HEADLESS: bool = False
    BROWSER_TIMEOUT_MS: int = 60000
    BROWSER_VIEWPORT_WIDTH: int = 1440
    BROWSER_VIEWPORT_HEIGHT: int = 900

    SAMPLE_EXPORT_DIR: str = "exports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
