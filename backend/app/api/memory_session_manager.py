"""
InMemorySessionManager - Session 테이블 없이 작동하는 간단한 세션 관리
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class InMemorySessionManager:
    """
    메모리 기반 세션 관리 (PostgreSQL 의존성 제거)

    Note:
        - Backend 재시작 시 세션 초기화됨
        - 프로덕션에서는 Redis/Memcached 권장
        - MVP/개발용으로 적합
    """

    def __init__(self, session_ttl_hours: int = 24):
        """
        초기화

        Args:
            session_ttl_hours: 세션 유효 시간 (시간)
        """
        self.session_ttl = timedelta(hours=session_ttl_hours)
        self._sessions: Dict[str, Dict] = {}

        logger.info(f"InMemorySessionManager initialized (TTL: {session_ttl_hours}h)")

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성 (메모리에 저장)

        Args:
            user_id: 사용자 ID (선택)
            metadata: 추가 메타데이터 (선택)

        Returns:
            (session_id, expires_at): 생성된 세션 ID와 만료 시각
        """
        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + self.session_ttl

        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": created_at,
            "expires_at": expires_at,
            "last_activity": created_at,
            "request_count": 0
        }

        logger.info(
            f"Session created (in-memory): {session_id} "
            f"(user: {user_id or 'anonymous'}, expires: {expires_at.isoformat()})"
        )

        return session_id, expires_at

    async def validate_session(self, session_id: str) -> bool:
        """
        세션 유효성 검증 (메모리 조회)

        Args:
            session_id: 검증할 세션 ID

        Returns:
            유효 여부
        """
        session = self._sessions.get(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False

        # 만료 체크
        if datetime.now(timezone.utc) > session["expires_at"]:
            logger.info(f"Session expired: {session_id}")
            del self._sessions[session_id]
            return False

        # 마지막 활동 시간 업데이트
        session["last_activity"] = datetime.now(timezone.utc)
        session["request_count"] += 1

        logger.debug(f"Session validated: {session_id}")
        return True

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회 (메모리)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 dict (없으면 None)
        """
        session = self._sessions.get(session_id)

        if not session:
            return None

        # 만료 체크
        if datetime.now(timezone.utc) > session["expires_at"]:
            del self._sessions[session_id]
            return None

        return session.copy()

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (로그아웃)

        Args:
            session_id: 삭제할 세션 ID

        Returns:
            삭제 성공 여부
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
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
        now = datetime.now(timezone.utc)
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if session["expires_at"] < now
        ]

        for sid in expired_sessions:
            del self._sessions[sid]

        count = len(expired_sessions)
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def get_active_session_count(self) -> int:
        """
        활성 세션 수 조회

        Returns:
            현재 활성 세션 수
        """
        now = datetime.now(timezone.utc)
        active_count = sum(
            1 for session in self._sessions.values()
            if session["expires_at"] > now
        )
        return active_count

    async def extend_session(self, session_id: str, hours: int = 24) -> bool:
        """
        세션 만료 시간 연장

        Args:
            session_id: 연장할 세션 ID
            hours: 연장할 시간 (시간)

        Returns:
            연장 성공 여부
        """
        session = self._sessions.get(session_id)

        if not session:
            return False

        # 이미 만료된 세션은 연장 불가
        if datetime.now(timezone.utc) > session["expires_at"]:
            return False

        new_expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        session["expires_at"] = new_expires_at

        logger.info(f"Session extended: {session_id} (+{hours}h)")
        return True


# === 전역 싱글톤 ===

_session_manager: Optional[InMemorySessionManager] = None


def get_in_memory_session_manager() -> InMemorySessionManager:
    """
    InMemorySessionManager 싱글톤 반환

    FastAPI Depends()에서 사용

    Returns:
        InMemorySessionManager 인스턴스
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = InMemorySessionManager(session_ttl_hours=24)

    return _session_manager


def reset_in_memory_session_manager():
    """
    SessionManager 초기화 (테스트용)
    """
    global _session_manager
    _session_manager = None


# === 호환성 레이어 (기존 코드 호환) ===

# 기존 SessionManager를 InMemorySessionManager로 대체
SessionManager = InMemorySessionManager
get_session_manager = get_in_memory_session_manager