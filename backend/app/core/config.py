from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_SECRET_KEYS = {
    "",
    "your-secret-key-change-this",
    "your-secret-key-change-this-in-production",
    "CHANGE_ME_SECRET_KEY_MIN_32_CHARS",
    "change-me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Project
    API_TITLE: str = "智获客 API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost/zhihuokeke"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "password"
    DATABASE_NAME: str = "zhihuokeke"
    DB_AUTO_CREATE_TABLES: bool = False

    # JWT
    SECRET_KEY: str = "CHANGE_ME_SECRET_KEY_MIN_32_CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MOBILE_H5_TICKET_EXPIRE_MINUTES: int = 10

    # 企业微信 OAuth（可选；不配置时 OAuth 入口自动隐藏，降级为短票据）
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_AGENT_SECRET: str = ""
    WECOM_OAUTH_SCOPE: str = "snsapi_base"  # snsapi_base | snsapi_privateinfo

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        secret = (value or "").strip()
        if secret in INSECURE_SECRET_KEYS:
            raise ValueError("SECRET_KEY 不能使用默认占位值，请在 .env 中配置随机强密钥")
        if len(secret) < 32:
            raise ValueError("SECRET_KEY 长度必须至少 32 个字符")
        return secret

    @model_validator(mode="after")
    def validate_cors_origins(self):
        if not self.DEBUG and "*" in self.CORS_ORIGINS:
            raise ValueError("生产环境禁止 CORS_ORIGINS 包含 '*'，请配置明确来源白名单")
        return self

    # AI Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2-chinese"
    USE_CLOUD_MODEL: bool = False

    # Fire Engine (Volcano Engine)
    ARK_API_KEY: str = ""
    ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    ARK_MODEL: str = "doubao-seed-2-0-mini-260215"
    ARK_TIMEOUT_SECONDS: int = 60
    ARK_VISION_RATE_LIMIT_PER_MINUTE: int = 20
    ARK_VISION_RATE_LIMIT_WINDOW_SECONDS: int = 60
    INSIGHT_BATCH_ANALYZE_RATE_LIMIT_PER_MINUTE: int = 6
    INSIGHT_BATCH_ANALYZE_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Redis (distributed rate limiting)
    USE_REDIS_RATE_LIMIT: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_KEY_PREFIX: str = "zhihuokeke"

    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    UPLOAD_DIR: str = "./uploads"

    # WeCom
    WECOM_WEBHOOK_URL: str = ""

    # Browser collector service
    BROWSER_COLLECTOR_BASE_URL: str = "http://127.0.0.1:8005"
    BROWSER_COLLECTOR_TIMEOUT_SECONDS: int = 180

settings = Settings()
