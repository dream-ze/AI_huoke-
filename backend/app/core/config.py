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
    ENABLE_STARTUP_USER_SEQUENCE_HEALTHCHECK: bool = True

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
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"  # 默认使用768维模型
    USE_CLOUD_MODEL: bool = False

    # Embedding 配置（向后兼容）
    EMBEDDING_DIMENSION: int = 768  # nomic-embed-text: 768
    
    # 火山方舟文本embedding模型（Task #10）
    ARK_EMBEDDING_MODEL: str = "doubao-embedding-large-text-240915"  # 2048维
    
    # 多模型池配置
    DEFAULT_EMBEDDING_MODEL: str = "doubao-embedding-large-text"  # Task #10: 默认使用火山方舟
    DEFAULT_LLM_MODEL: str = "qwen2.5"

    @property
    def EMBEDDING_MODELS(self) -> dict:
        """Embedding模型池配置"""
        return {
            # 火山方舟文本embedding（Task #10: 优先使用）
            "doubao-embedding-large-text": {
                "provider": "ark",
                "dimension": 2048,
                "description": "火山方舟文本embedding（优先）",
                "ark_model": "doubao-embedding-large-text-240915"
            },
            # Ollama 本地模型（降级备选）
            "nomic-embed-text": {
                "provider": "ollama",
                "dimension": 768,
                "description": "轻量级本地模型（降级备选）",
                "ollama_name": "nomic-embed-text"
            },
            "qwen3-embedding": {
                "provider": "ollama",
                "dimension": 1024,
                "description": "通义千问嵌入",
                "ollama_name": "qwen3-embedding"
            },
            "all-minilm": {
                "provider": "ollama",
                "dimension": 384,
                "description": "最小化模型",
                "ollama_name": "all-minilm"
            },
        }

    @property
    def LLM_MODELS(self) -> dict:
        """LLM模型池配置"""
        return {
            "qwen2.5": {
                "provider": "ollama",
                "description": "本地通义千问",
                "ollama_name": "qwen2.5"
            },
            "doubao-1-5-pro-32k": {
                "provider": "ark",
                "description": "火山方舟豆包",
                "ark_model": "doubao-1-5-pro-32k-250115"
            },
        }

    # Fire Engine (Volcano Engine)
    ARK_API_KEY: str = ""
    ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    ARK_MODEL: str = "doubao-seed-2-0-mini-260215"
    # Responses API (多模态，seed模型)
    ARK_SEED_API_KEY: str = ""
    ARK_SEED_MODEL: str = "doubao-seed-2-0-mini-260215"
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
