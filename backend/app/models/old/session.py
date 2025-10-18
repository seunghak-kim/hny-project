"""
Session Model for PostgreSQL/SQLite

WebSocket 세션 관리를 위한 SQLAlchemy 모델
SessionManager에서 사용
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.sql import func
from app.db.postgre_db import Base


class Session(Base):
    """
    WebSocket 세션 모델

    SQLite/PostgreSQL 모두 호환
    기존 session_manager.py의 SQLite 스키마와 동일
    """
    __tablename__ = "sessions"

    # Primary Key
    session_id = Column(String(100), primary_key=True, index=True)

    # User & Metadata
    user_id = Column(Integer, nullable=True, index=True)
    session_metadata = Column("metadata", Text, nullable=True)  # JSON string (mapped to 'metadata' in DB)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    last_activity = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Statistics
    request_count = Column(Integer, default=0, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),
    )
