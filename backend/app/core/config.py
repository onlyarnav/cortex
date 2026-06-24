from pathlib import Path
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    @field_validator("DATABASE_URL")
    @classmethod
    def fix_db_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgresql://") and "+psycopg2" not in v:
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # Redis / Celery
    REDIS_URL: str

    # Qdrant
    QDRANT_URL: str

    # LLM
    GROQ_API_KEY: str
    LLM_MODEL: str = "llama-3.1-8b-instant"

    # Embeddings
    HF_TOKEN: str = ""

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = str(ENV_PATH)
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()