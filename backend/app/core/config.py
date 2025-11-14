from typing import List
from pydantic import Field
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

    # ============================================================================
    # Session & Memory Configuration
    # ============================================================================
    SESSION_TTL_HOURS: int = 24
    MEMORY_RETENTION_DAYS: int = 90
    MEMORY_LIMIT_PER_USER: int = 100

    # Long-term Memory 범위 설정
    MEMORY_LOAD_LIMIT: int = 5  # Number of recent memories to load per user

    # === 3-Tier Memory Configuration ===
    SHORTTERM_MEMORY_LIMIT: int = Field(
        default=5,
        description="최근 N개 세션 전체 메시지 로드 (1-5 세션)"
    )

    MIDTERM_MEMORY_LIMIT: int = Field(
        default=5,
        description="중기 메모리 세션 수 (6-10번째 세션)"
    )

    LONGTERM_MEMORY_LIMIT: int = Field(
        default=10,
        description="장기 메모리 세션 수 (11-20번째 세션)"
    )

    MEMORY_TOKEN_LIMIT: int = Field(
        default=2000,
        description="메모리 로드 시 최대 토큰 제한"
    )

    MEMORY_MESSAGE_LIMIT: int = Field(
        default=10,
        description="Short-term 세션당 최대 메시지 수"
    )

    SUMMARY_MAX_LENGTH: int = Field(
        default=200,
        description="LLM 요약 최대 글자 수"
    )

    # ============================================================================
    # Data Reuse Configuration
    # ============================================================================
    DATA_REUSE_MESSAGE_LIMIT: int = Field(
        default=5,
        description="최근 N개 메시지 내 데이터 재사용 (0=비활성화)"
    )

    # 메모리 공유 범위 가이드:
    # -------------------------
    # 이 설정은 user_id 기반으로 최근 N개 세션의 메모리를 로드합니다.
    # 같은 유저의 여러 대화창(세션) 간 메모리 공유 범위를 제어합니다.
    #
    # 설정 값별 동작:
    #   0  : 다른 세션 기억 안 함 (현재 대화창만, 완전 격리)
    #        - 프라이버시가 중요한 경우
    #        - 각 대화가 독립적인 경우
    #
    #   1  : 최근 1개 세션만 기억
    #        - 최소한의 문맥 유지
    #        - 메모리 사용 최소화
    #
    #   3  : 최근 3개 세션 기억 (적당한 균형)
    #        - 일반적인 사용 케이스
    #        - 성능과 문맥의 균형
    #
    #   5  : 최근 5개 세션 기억 (기본값, 권장)
    #        - 여러 대화창 간 자연스러운 문맥 공유
    #        - 적당한 메모리 사용
    #
    #   10 : 최근 10개 세션 기억 (긴 기억)
    #        - 장기 프로젝트나 상담
    #        - 오랜 기간 문맥 유지 필요
    #
    # 사용 방법:
    #   1. .env 파일에 MEMORY_LOAD_LIMIT=N 추가
    #   2. 서버 재시작
    #   3. 새로운 설정이 적용됨
    #
    # 예시:
    #   # .env 파일
    #   MEMORY_LOAD_LIMIT=0   # 세션별 완전 격리
    #   MEMORY_LOAD_LIMIT=3   # 최근 3개만
    #   MEMORY_LOAD_LIMIT=10  # 긴 기억
    #
    # 참고:
    #   - 현재 진행 중인 세션은 항상 자동 제외됩니다 (불완전한 데이터 방지)
    #   - user_id 기반이므로 같은 유저의 모든 세션에서 검색합니다
    #   - 자세한 내용은 reports/Manual/MEMORY_CONFIGURATION_GUIDE.md 참조

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