"""
PostgreSQL-based Session Manager (SQLAlchemy ORM)
Persistent session storage that survives backend restarts

Migrated from SQLite (sqlite3) to PostgreSQL (SQLAlchemy Async)
"""

import uuid
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import AsyncSessionLocal
from app.models.session import Session
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    PostgreSQL 기반 세션 관리 (SQLAlchemy ORM)

    Backend 재시작 시에도 세션 유지
    비동기 처리로 FastAPI와 완벽 호환
    """

    def __init__(self, session_ttl_hours: int = 24):
        """
        초기화

        Args:
            session_ttl_hours: 세션 유효 시간 (시간)
        """
        self.session_ttl = timedelta(hours=session_ttl_hours)

        logger.info(
            f"PostgreSQLSessionManager initialized (TTL: {session_ttl_hours}h)"
        )

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성 (PostgreSQL에 저장)

        Args:
            user_id: 사용자 ID (선택)
            metadata: 추가 메타데이터 (선택)

        Returns:
            (session_id, expires_at): 생성된 세션 ID와 만료 시각
        """
        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + self.session_ttl

        async with AsyncSessionLocal() as db:
            new_session = Session(
                session_id=session_id,
                user_id=user_id,
                session_metadata=json.dumps(metadata or {}),
                created_at=created_at,
                expires_at=expires_at,
                last_activity=created_at,
                request_count=0
            )
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)

        logger.info(
            f"Session created (PostgreSQL): {session_id} "
            f"(user: {user_id or 'anonymous'}, expires: {expires_at.isoformat()})"
        )

        return session_id, expires_at

    async def validate_session(self, session_id: str) -> bool:
        """
        세션 유효성 검증 (PostgreSQL 조회)

        Args:
            session_id: 검증할 세션 ID

        Returns:
            유효 여부
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Session not found: {session_id}")
                return False

            # 만료 체크
            if datetime.now(timezone.utc) > session.expires_at:
                logger.info(f"Session expired: {session_id}")
                # 만료된 세션 삭제
                await db.delete(session)
                await db.commit()
                return False

            # 마지막 활동 시간 업데이트
            session.last_activity = datetime.now(timezone.utc)
            session.request_count += 1
            await db.commit()

            logger.debug(f"Session validated: {session_id}")
            return True

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회 (PostgreSQL)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 dict (없으면 None)
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return None

            # 만료 체크
            if datetime.now(timezone.utc) > session.expires_at:
                # 만료된 세션 삭제
                await db.delete(session)
                await db.commit()
                return None

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "metadata": json.loads(session.session_metadata) if session.session_metadata else {},
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "last_activity": session.last_activity,
                "request_count": session.request_count
            }

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (로그아웃)

        Args:
            session_id: 삭제할 세션 ID

        Returns:
            삭제 성공 여부
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(Session).where(Session.session_id == session_id)
            )
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"Session deleted: {session_id}")
                return True

            logger.warning(f"Session not found for deletion: {session_id}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        만료된 세션 정리

        Returns:
            정리된 세션 수
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(Session).where(Session.expires_at < datetime.now(timezone.utc))
            )
            await db.commit()
            count = result.rowcount

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def get_active_session_count(self) -> int:
        """
        활성 세션 수 조회

        Returns:
            현재 활성 세션 수
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count(Session.session_id)).where(
                    Session.expires_at > datetime.now(timezone.utc)
                )
            )
            count = result.scalar()

        return count or 0

    async def extend_session(self, session_id: str, hours: int = 24) -> bool:
        """
        세션 만료 시간 연장

        Args:
            session_id: 연장할 세션 ID
            hours: 연장할 시간 (시간)

        Returns:
            연장 성공 여부
        """
        new_expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(Session)
                .where(
                    Session.session_id == session_id,
                    Session.expires_at > datetime.now(timezone.utc)
                )
                .values(expires_at=new_expires_at)
            )
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"Session extended: {session_id} (+{hours}h)")
                return True

            return False


# === 전역 싱글톤 ===

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    SessionManager 싱글톤 인스턴스 반환

    FastAPI Depends()에서 사용

    Returns:
        SessionManager 인스턴스 (PostgreSQL 기반)
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(session_ttl_hours=settings.SESSION_TTL_HOURS)

    return _session_manager


def reset_session_manager():
    """
    SessionManager 초기화 (테스트용)
    """
    global _session_manager
    _session_manager = None
