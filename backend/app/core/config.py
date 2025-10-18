from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HolmesNyangz"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = ""
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    MONGODB_URL: str = ""
    real_estate_data_path: str = "frontend/public/data/real_estate_with_coordinates_kakao.csv"

    # ============================================================================
    # PostgreSQL Configuration (Centralized)
    # ============================================================================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root1234"
    POSTGRES_DB: str = "real_estate"

    # Session & Memory Configuration
    SESSION_TTL_HOURS: int = 24
    MEMORY_RETENTION_DAYS: int = 90
    MEMORY_LIMIT_PER_USER: int = 100
    MEMORY_LOAD_LIMIT: int = 5  # Number of recent memories to load per user

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env file

    @property
    def postgres_url(self) -> str:
        """
        PostgreSQL 연결 문자열 (LangGraph Checkpoint용)

        DATABASE_URL이 있으면 우선 사용하되, '+psycopg' 제거
        (LangGraph는 순수 postgresql:// 형식 필요)
        """
        if self.DATABASE_URL:
            # SQLAlchemy 형식 (postgresql+psycopg://) → LangGraph 형식 (postgresql://)
            return self.DATABASE_URL.replace("+psycopg", "")

        # DATABASE_URL이 없으면 개별 설정으로 생성
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sqlalchemy_url(self) -> str:
        """
        SQLAlchemy 연결 문자열 (postgre_db.py, Long-term Memory용)

        DATABASE_URL 그대로 사용 (postgresql+psycopg:// 유지)
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # DATABASE_URL이 없으면 개별 설정으로 생성 (psycopg 포함)
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()