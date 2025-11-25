from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Text,
    Enum,
    Index,
    CheckConstraint,
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
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, nullable=False)
    type = Column(Enum(UserType), default=UserType.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
class LocalAuth(Base):
    __tablename__ = "local_auths"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class SocialAuth(Base):
    __tablename__ = "social_auths"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    provider = Column(Enum(SocialProvider), nullable= False)
    provider_user_id = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    
    # 복합 유니크 제약 조건 추가
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='idx_provider_user'),
    )

class UserFavorite(Base):
    __tablename__ = "user_favorites"
    id = Column(Integer, primary_key= True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    building_id = Column(Integer, ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # 유니크 제약 조건 추가
    __table_args__ = (
        UniqueConstraint('user_id', 'building_id', name='idx_user_building'),
    )
    
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    nickname = Column(String(20), nullable=False)
    bio = Column(Text, nullable=True) # 자기소개 한줄 같은거 
    gender = Column(Enum(Gender), nullable=True)
    birhthdate = Column(String(8), nullable=False) # YYYYMMDD
    image_url = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_profiles_user_id'),
        UniqueConstraint('nickname', name='uq_user_profiles_nickname'),
    )
    

    
    