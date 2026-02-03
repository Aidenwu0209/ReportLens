"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration – values come from .env or environment."""

    # ── App ──────────────────────────────────────────────
    APP_ENV: str = "dev"
    APP_BASE_URL: str = "http://localhost:8000"
    APP_JWT_SECRET: str = "change_me_please"
    APP_JWT_EXPIRE_MIN: int = 120

    # ── Storage ──────────────────────────────────────────
    DATA_ROOT: str = "./data"
    STORAGE_BACKEND: str = "localfs"  # localfs | s3

    # ── MySQL ────────────────────────────────────────────
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "annual_ai"
    MYSQL_USER: str = "annual_ai_user"
    MYSQL_PASSWORD: str = "annual_ai_pass"
    SQLALCHEMY_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── Vector (optional) ────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    VECTOR_BACKEND: str = "none"  # qdrant | none

    # ── PaddleOCR-VL 1.5 ────────────────────────────────
    PADDLEOCR_VL_API_BASE: str = "http://localhost:9000"
    PADDLEOCR_VL_API_KEY: str = ""
    PADDLEOCR_VL_TIMEOUT_SEC: int = 60
    PADDLEOCR_VL_MAX_RPS: int = 5

    # ── Wenxin 5.0 ──────────────────────────────────────
    WENXIN_API_BASE: str = "https://aip.baidubce.com"
    WENXIN_API_KEY: str = ""
    WENXIN_MODEL: str = "ernie-5.0"
    WENXIN_TIMEOUT_SEC: int = 90
    WENXIN_MAX_RPS: int = 2

    # ── Export ───────────────────────────────────────────
    EXPORT_TEMPLATE_VER: str = "tpl_001"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            "?charset=utf8mb4"
        )

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace("mysql+pymysql", "mysql+aiomysql")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
