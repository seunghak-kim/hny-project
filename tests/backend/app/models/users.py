from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Text,
    Enum,
    Index,
    UniqueConstraint
)
from sqlalchemy.sql import func 
from app.db.postgre_db import Base
from sqlalchemy.orm import relationship
import enum

class UserType(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class SocialProvider(enum.Enum):
    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"
    APPLE = "apple"

class User(Base):
    """통합 사용자 테이블"""
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True, comment="이메일 (중복 가입 방지)")
    username = Column(String(50), nullable=True, comment="사용자 이름")
    is_active = Column(Boolean, default=True, comment="계정 활성화 여부")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="계정 생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="계정 수정일")

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    local_auth = relationship("LocalAuth", back_populates="user", uselist=False, cascade="all, delete-orphan")
    social_auths = relationship("SocialAuth", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class LocalAuth(Base):
    """로컬 로그인 인증 정보"""
    __tablename__ = "local_auths"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="사용자 ID (1명당 로컬 인증 1개만)")
    hashed_password = Column(String(255), nullable=False, comment="암호화된 비밀번호")
    password_changed_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="비밀번호 변경일")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    user = relationship("User", back_populates="local_auth")


class UserProfile(Base):
    """사용자 프로필"""
    __tablename__ = "user_profiles"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="사용자 ID")
    nickname = Column(String(20), nullable=False, unique=True, comment="닉네임")
    bio = Column(Text, nullable=True, comment="소개글")
    gender = Column(Enum(Gender), nullable=False, comment="성별")
    birth_date = Column(String(8), nullable=False, comment="YYYYMMDD 형식의 생년월일")
    image_url = Column(String(500), nullable=True, comment="프로필 사진 URL")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="프로필 생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="프로필 수정일")

    # Relationships
    user = relationship("User", back_populates="profile")

class SocialAuth(Base):
    """소셜 로그인 인증 정보 (한 사용자가 여러 소셜 계정 연동 가능)"""
    __tablename__ = "social_auths"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="사용자 ID")
    provider = Column(Enum(SocialProvider), nullable=False, comment="소셜 로그인 제공자")
    provider_id = Column(String(255), nullable=False, comment="제공자가 준 고유 ID")
    provider_email = Column(String(255), nullable=True, comment="소셜 제공자 이메일")
    provider_name = Column(String(100), nullable=True, comment="소셜 제공자 이름")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="연동일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    user = relationship("User", back_populates="social_auths")

    # Indexes & Constraints
    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uk_provider'), # 같은 소셜 계정 중복 방지
        UniqueConstraint('user_id', 'provider', name='uk_user_provider'), # 1명당 provider별 1개만
        Index('idx_social_auth_user_id', 'user_id'),
    )


class UserFavorite(Base):
    """사용자 찜 목록"""
    __tablename__ = "user_favorites"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="사용자 ID")
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"), nullable=False, comment="부동산 ID")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    user = relationship("User", back_populates="favorites")
    real_estate = relationship("RealEstate")

    # Indexes
    __table_args__ = (
        Index('idx_user_real_estate', 'user_id', 'real_estate_id', unique=True),
    )
