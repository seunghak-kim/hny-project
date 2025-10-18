"""
Long-term Memory Models for User Conversation History
Stores conversation memories, user preferences, and entity tracking
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    TIMESTAMP,
    ForeignKey,
    Index,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid


class ConversationMemory(Base):
    """
    대화 기록 저장 (Long-term Memory)

    사용자의 과거 대화 내용을 저장하여 문맥 유지
    """
    __tablename__ = "conversation_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="사용자 ID"
    )

    # 대화 내용
    query = Column(Text, nullable=False, comment="사용자 쿼리")
    response_summary = Column(Text, nullable=False, comment="응답 요약")

    # 분석 결과 (JSONB for flexibility)
    relevance = Column(String(20), nullable=False, comment="관련성 (RELEVANT/IRRELEVANT)")
    intent_detected = Column(String(50), comment="감지된 의도")
    entities_mentioned = Column(JSONB, comment="언급된 엔티티 (매물/지역/중개사)")

    # 메타데이터
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성일"
    )
    conversation_metadata = Column(JSONB, comment="추가 메타데이터 (teams_used, response_time 등)")

    # Dynamic Session ID (연결)
    session_id = Column(
        String(100),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="채팅 세션 ID (Chat History & State Endpoints)"
    )

    # Relationships
    user = relationship("User", back_populates="conversation_memories")
    chat_session = relationship("ChatSession", back_populates="conversation_memories")

    # Indexes for performance
    __table_args__ = (
        Index('idx_conv_mem_user_created', 'user_id', 'created_at'),
        Index('idx_conv_mem_relevance', 'relevance'),
        Index('idx_conv_mem_session_id', 'session_id'),
        Index('idx_conv_mem_session_created', 'session_id', 'created_at'),
    )


class UserPreference(Base):
    """
    사용자 선호도 추적

    사용자가 반복적으로 사용하는 패턴, 선호하는 응답 스타일 저장
    """
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One preference record per user
        comment="사용자 ID"
    )

    # 선호도 데이터 (JSONB for flexibility)
    preferences = Column(
        JSONB,
        nullable=False,
        default={},
        comment="사용자 선호도 JSON (preferred_regions, preferred_property_types, response_style 등)"
    )

    # 메타데이터
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성일"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="수정일"
    )

    # Relationships
    user = relationship("User", back_populates="preferences")


class EntityMemory(Base):
    """
    엔티티 추적 (매물/지역/중개사)

    사용자가 과거에 언급했던 특정 엔티티 기록
    """
    __tablename__ = "entity_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="사용자 ID"
    )

    # 엔티티 정보
    entity_type = Column(
        String(50),
        nullable=False,
        comment="엔티티 타입 (property/region/agent)"
    )
    entity_id = Column(String(100), nullable=False, comment="엔티티 식별자")
    entity_name = Column(String(200), comment="엔티티 이름")

    # 추적 정보
    mention_count = Column(Integer, default=1, comment="언급 횟수")
    first_mentioned_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="첫 언급일"
    )
    last_mentioned_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="마지막 언급일"
    )

    # 추가 컨텍스트
    entity_context = Column(JSONB, comment="엔티티 관련 컨텍스트 (사용자 관심사항 등)")

    # Relationships
    user = relationship("User", back_populates="entity_memories")

    # Indexes and Constraints
    __table_args__ = (
        Index('idx_entity_mem_user_type', 'user_id', 'entity_type'),
        Index('idx_entity_mem_entity', 'entity_type', 'entity_id'),
        UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_entity'),
    )
