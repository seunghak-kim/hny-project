"""
Chat Session Models - Aligned with PostgreSQL Schema
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid


class ChatSession(Base):
    """
    채팅 세션 (Chat History & State Endpoints)

    PostgreSQL 스키마와 정확히 일치
    """
    __tablename__ = "chat_sessions"

    # Primary Key - DB와 일치 (session_id VARCHAR(100))
    session_id = Column(
        String(100),
        primary_key=True,
        comment="세션 고유 식별자"
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="사용자 ID"
    )

    # 세션 정보
    title = Column(
        String(200),  # DB: VARCHAR(200)
        nullable=False,
        default="새 대화",
        comment="세션 제목"
    )

    last_message = Column(
        Text,
        comment="마지막 메시지 미리보기"
    )

    message_count = Column(
        Integer,
        default=0,
        comment="세션 내 메시지 개수"
    )

    # 타임스탬프
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성일"
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="마지막 활동일"
    )

    # 상태
    is_active = Column(
        Boolean,
        default=True,
        comment="세션 활성 상태"
    )

    # 메타데이터 - 'metadata'는 SQLAlchemy 예약어이므로 session_metadata로 매핑
    session_metadata = Column(
        "metadata",  # DB 컬럼명은 'metadata'
        JSONB,
        comment="추가 메타데이터"
    )

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    # Indexes (DB에 이미 존재)
    __table_args__ = (
        Index('idx_chat_sessions_user_id', 'user_id'),
        Index('idx_chat_sessions_updated_at', 'updated_at'),
        Index('idx_chat_sessions_user_updated', 'user_id', 'updated_at'),
    )

    def __repr__(self):
        return f"<ChatSession(session_id='{self.session_id}', title='{self.title}')>"


class ChatMessage(Base):
    """채팅 메시지 모델"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # session_id를 String으로 변경 (ChatSession.session_id가 VARCHAR이므로)
    session_id = Column(
        String(100),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="세션 ID"
    )

    role = Column(
        String(20),
        nullable=False,
        comment="메시지 역할 (user/assistant/system)"
    )

    content = Column(
        Text,
        nullable=False,
        comment="메시지 내용"
    )

    # 구조화된 데이터 (sections, metadata 등)
    structured_data = Column(
        JSONB,
        nullable=True,
        comment="구조화된 답변 데이터 (sections, metadata)"
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="생성일"
    )

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
