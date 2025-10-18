"""
Unified Database Schema for HolmesNyangz
=========================================

This module contains ALL database table definitions in one place for clarity.

Tables (9 total):
1. Session - HTTP/WebSocket session management
2. ChatSession - Chat History & State Endpoints
3. ChatMessage - Chat message storage
4. ConversationMemory - Long-term memory (conversation history)
5. EntityMemory - Entity tracking
6. Checkpoint - LangGraph checkpoint
7. CheckpointBlob - LangGraph checkpoint blobs
8. CheckpointWrite - LangGraph checkpoint writes
9. CheckpointMigration - LangGraph checkpoint migrations

Date: 2025-10-14
Author: Claude Code
"""

from sqlalchemy import (
    Column, String, Integer, Text, Boolean, Float, TIMESTAMP,
    ForeignKey, CheckConstraint, Index, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ============================================================================
# Core Tables (5 tables)
# ============================================================================

class Session(Base):
    """
    HTTP/WebSocket 세션 관리

    - FastAPI session management
    - Tracks user sessions, expiration, and activity
    - Different from ChatSession (chat-specific sessions)
    """
    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_activity = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    metadata = Column(JSONB)

    # Indexes
    __table_args__ = (
        Index('idx_sessions_expires_at', 'expires_at'),
        Index('idx_sessions_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id})>"


class ChatSession(Base):
    """
    Chat History & State Endpoints

    - Each chat session is an independent conversation thread
    - Chat History & State Endpoints
    - Auto-generates title from first message via trigger
    """
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False, default="새 대화")
    last_message = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    is_active = Column(Boolean, default=True)
    session_metadata = Column("metadata", JSONB)  # 'metadata' is reserved in SQLAlchemy

    # Relationships
    chat_messages = relationship(
        "ChatMessage",
        back_populates="chat_session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    conversation_memories = relationship(
        "ConversationMemory",
        back_populates="chat_session",
        cascade="all, delete-orphan",
        order_by="ConversationMemory.created_at"
    )

    # Indexes
    __table_args__ = (
        Index('idx_chat_sessions_user_id', 'user_id'),
        Index('idx_chat_sessions_updated_at', 'updated_at', postgresql_using='btree', postgresql_ops={'updated_at': 'DESC'}),
        Index('idx_chat_sessions_user_updated', 'user_id', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        Index('idx_chat_sessions_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<ChatSession(session_id='{self.session_id}', title='{self.title}', message_count={self.message_count})>"


class ChatMessage(Base):
    """
    채팅 메시지 저장 (선택적 사용)

    - Alternative to storing in conversation_memories
    - More granular message tracking
    - role: 'user', 'assistant', 'system'
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(100),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    metadata = Column(JSONB)

    # Relationships
    chat_session = relationship("ChatSession", back_populates="chat_messages")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name='check_chat_message_role'),
        Index('idx_chat_messages_session_id', 'session_id'),
        Index('idx_chat_messages_session_created', 'session_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id='{self.session_id}')>"


class ConversationMemory(Base):
    """
    Long-term Memory (대화 기록)

    - Stores user queries and AI responses
    - Used for context retrieval and personalization
    - Links to ChatSession via session_id (nullable for backward compatibility)
    - Relevance: 'RELEVANT', 'IRRELEVANT', 'UNCLEAR'
    """
    __tablename__ = "conversation_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(Integer, nullable=False)
    query = Column(Text, nullable=False)
    response_summary = Column(Text, nullable=False)
    relevance = Column(String(20), nullable=False)
    session_id = Column(
        String(100),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=True
    )
    intent_detected = Column(String(100), nullable=True)
    entities_mentioned = Column(JSONB)
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    conversation_metadata = Column(JSONB)

    # Relationships
    chat_session = relationship("ChatSession", back_populates="conversation_memories")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "relevance IN ('RELEVANT', 'IRRELEVANT', 'UNCLEAR')",
            name='check_conversation_memory_relevance'
        ),
        Index('idx_conv_mem_user_id', 'user_id'),
        Index('idx_conv_mem_created_at', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_conv_mem_relevance', 'relevance'),
        Index('idx_conv_mem_session_id', 'session_id'),
        Index('idx_conv_mem_session_created', 'session_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
    )

    def __repr__(self):
        return f"<ConversationMemory(id='{self.id}', user_id={self.user_id}, relevance='{self.relevance}')>"


class EntityMemory(Base):
    """
    Entity 추적 (사용자 언급 엔티티)

    - Tracks entities mentioned by users (names, addresses, properties, etc.)
    - Used for context and personalization
    - importance_score: 0.0 ~ 1.0
    """
    __tablename__ = "entity_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(Integer, nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_name = Column(String(200), nullable=False)
    entity_value = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    first_mentioned = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_mentioned = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    mention_count = Column(Integer, default=1)
    importance_score = Column(Float, default=0.5)
    metadata = Column(JSONB)

    # Indexes
    __table_args__ = (
        Index('idx_entity_mem_user_id', 'user_id'),
        Index('idx_entity_mem_type', 'entity_type'),
        Index('idx_entity_mem_name', 'entity_name'),
        Index('idx_entity_mem_last_mentioned', 'last_mentioned', postgresql_ops={'last_mentioned': 'DESC'}),
    )

    def __repr__(self):
        return f"<EntityMemory(id='{self.id}', entity_type='{self.entity_type}', entity_name='{self.entity_name}')>"


# ============================================================================
# LangGraph Checkpoint Tables (4 tables)
# ============================================================================

class Checkpoint(Base):
    """
    LangGraph 체크포인트

    - Stores LangGraph execution state
    - Enables pause/resume of agent workflows
    - Required by AsyncPostgresSaver
    """
    __tablename__ = "checkpoints"

    thread_id = Column(Text, primary_key=True, nullable=False)
    checkpoint_ns = Column(Text, primary_key=True, nullable=False, default='')
    checkpoint_id = Column(Text, primary_key=True, nullable=False)
    parent_checkpoint_id = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    checkpoint = Column(JSONB, nullable=False)
    metadata = Column(JSONB, nullable=False, default={})

    # Indexes
    __table_args__ = (
        Index('idx_checkpoints_thread_id', 'thread_id'),
    )

    def __repr__(self):
        return f"<Checkpoint(thread_id='{self.thread_id}', checkpoint_id='{self.checkpoint_id}')>"


class CheckpointBlob(Base):
    """
    LangGraph 체크포인트 바이너리 데이터

    - Stores binary data associated with checkpoints
    - Used for large objects that don't fit in JSONB
    """
    __tablename__ = "checkpoint_blobs"

    thread_id = Column(Text, primary_key=True, nullable=False)
    checkpoint_ns = Column(Text, primary_key=True, nullable=False, default='')
    channel = Column(Text, primary_key=True, nullable=False)
    version = Column(Text, primary_key=True, nullable=False)
    type = Column(Text, nullable=False)
    blob = Column(BYTEA, nullable=True)

    def __repr__(self):
        return f"<CheckpointBlob(thread_id='{self.thread_id}', channel='{self.channel}')>"


class CheckpointWrite(Base):
    """
    LangGraph 체크포인트 쓰기 기록

    - Tracks writes to checkpoint state
    - Enables incremental state updates
    """
    __tablename__ = "checkpoint_writes"

    thread_id = Column(Text, primary_key=True, nullable=False)
    checkpoint_ns = Column(Text, primary_key=True, nullable=False, default='')
    checkpoint_id = Column(Text, primary_key=True, nullable=False)
    task_id = Column(Text, primary_key=True, nullable=False)
    idx = Column(Integer, primary_key=True, nullable=False)
    channel = Column(Text, nullable=False)
    type = Column(Text, nullable=True)
    blob = Column(BYTEA, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_checkpoint_writes_thread_id', 'thread_id'),
    )

    def __repr__(self):
        return f"<CheckpointWrite(thread_id='{self.thread_id}', checkpoint_id='{self.checkpoint_id}', task_id='{self.task_id}')>"


class CheckpointMigration(Base):
    """
    LangGraph 체크포인트 마이그레이션 버전

    - Tracks checkpoint schema migrations
    - Used by AsyncPostgresSaver for version management
    """
    __tablename__ = "checkpoint_migrations"

    v = Column(Integer, primary_key=True)

    def __repr__(self):
        return f"<CheckpointMigration(version={self.v})>"


# ============================================================================
# Metadata and Summary
# ============================================================================

# All models in this module
ALL_MODELS = [
    Session,
    ChatSession,
    ChatMessage,
    ConversationMemory,
    EntityMemory,
    Checkpoint,
    CheckpointBlob,
    CheckpointWrite,
    CheckpointMigration
]

# Model names for easy reference
MODEL_NAMES = [model.__tablename__ for model in ALL_MODELS]

# Summary
SCHEMA_SUMMARY = {
    "total_tables": len(ALL_MODELS),
    "core_tables": 5,
    "checkpoint_tables": 4,
    "tables": MODEL_NAMES
}


def create_all_tables(engine):
    """
    Create all tables defined in this schema.

    Usage:
        from sqlalchemy import create_engine
        from app.models.unified_schema import create_all_tables

        engine = create_engine('postgresql+psycopg://...')
        create_all_tables(engine)

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)
    print(f"✅ Created {len(ALL_MODELS)} tables: {', '.join(MODEL_NAMES)}")


def drop_all_tables(engine):
    """
    Drop all tables defined in this schema.

    WARNING: This will delete all data!

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(engine)
    print(f"🗑️ Dropped {len(ALL_MODELS)} tables: {', '.join(MODEL_NAMES)}")


def print_schema_info():
    """Print schema information."""
    print("=" * 60)
    print("HolmesNyangz Database Schema")
    print("=" * 60)
    print(f"Total Tables: {SCHEMA_SUMMARY['total_tables']}")
    print(f"Core Tables: {SCHEMA_SUMMARY['core_tables']}")
    print(f"Checkpoint Tables: {SCHEMA_SUMMARY['checkpoint_tables']}")
    print()
    print("Tables:")
    for i, name in enumerate(MODEL_NAMES, 1):
        print(f"  {i}. {name}")
    print("=" * 60)


if __name__ == "__main__":
    # Print schema info when run directly
    print_schema_info()
