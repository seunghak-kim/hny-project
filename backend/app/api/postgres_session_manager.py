"""
PostgreSQL Session Manager - chat_sessions 테이블 사용
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.db.postgre_db import get_async_db

logger = logging.getLogger(__name__)


class PostgreSQLSessionManager:
    """
    PostgreSQL 기반 세션 관리 (chat_sessions 테이블 사용)

    Note:
        - chat_sessions 테이블에 세션 저장
        - 서버 재시작해도 세션 유지됨
        - 프로덕션 환경에 적합
    """

    def __init__(self, session_ttl_hours: int = 24):
        """
        초기화

        Args:
            session_ttl_hours: 세션 유효 시간 (시간) - 현재 미사용 (추후 구현)
        """
        self.session_ttl = timedelta(hours=session_ttl_hours)
        logger.info(f"PostgreSQLSessionManager initialized (TTL: {session_ttl_hours}h)")

    async def create_session(
        self,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성 (chat_sessions 테이블에 저장)

        Args:
            user_id: 사용자 ID (기본값: 1)
            metadata: 추가 메타데이터 (현재 미사용)

        Returns:
            (session_id, expires_at): 생성된 세션 ID와 만료 시각
        """
        session_id = f"session-{uuid.uuid4()}"
        user_id = user_id or 1  # 기본값: 1 (인증 미구현)

        # DB 세션 가져오기
        result = None
        async for db_session in get_async_db():
            try:
                # 새 세션 생성
                new_session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    title="새 대화"
                )
                db_session.add(new_session)
                await db_session.commit()
                await db_session.refresh(new_session)

                # 만료 시간 계산 (현재는 고정값)
                expires_at = datetime.now(timezone.utc) + self.session_ttl

                logger.info(
                    f"Session created (PostgreSQL): {session_id} "
                    f"(user: {user_id}, expires: {expires_at.isoformat()})"
                )

                result = (session_id, expires_at)

            except Exception as e:
                await db_session.rollback()
                logger.error(f"Failed to create session: {e}")
                raise
            finally:
                break  # generator 종료

        return result

    async def validate_session(self, session_id: str) -> bool:
        """
        세션 유효성 검증 (chat_sessions 테이블 조회)

        Args:
            session_id: 검증할 세션 ID

        Returns:
            유효 여부
        """
        result_value = False
        async for db_session in get_async_db():
            try:
                # 세션 조회
                query = select(ChatSession).where(ChatSession.session_id == session_id)
                result = await db_session.execute(query)
                session = result.scalar_one_or_none()

                if not session:
                    logger.warning(f"Session not found: {session_id}")
                    result_value = False
                else:
                    # updated_at 갱신 (트리거가 자동으로 처리)
                    await db_session.execute(
                        update(ChatSession)
                        .where(ChatSession.session_id == session_id)
                        .values(updated_at=datetime.now(timezone.utc))
                    )
                    await db_session.commit()

                    logger.debug(f"Session validated: {session_id}")
                    result_value = True

            except Exception as e:
                logger.error(f"Failed to validate session: {e}")
                result_value = False
            finally:
                break

        return result_value

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회 (chat_sessions 테이블)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 dict (없으면 None)
        """
        async for db_session in get_async_db():
            try:
                # 세션 조회
                query = select(ChatSession).where(ChatSession.session_id == session_id)
                result = await db_session.execute(query)
                session = result.scalar_one_or_none()

                if not session:
                    return None

                return {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "expires_at": session.created_at + self.session_ttl,  # 계산값
                    "last_activity": session.updated_at  # ✅ P1 버그 수정: last_activity 키 추가
                }

            except Exception as e:
                logger.error(f"Failed to get session: {e}")
                return None
            finally:
                break

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (chat_sessions 테이블에서 삭제)

        Note:
            - chat_messages도 CASCADE로 자동 삭제됨
            - checkpoints도 수동 삭제 필요 (FK 없음)

        Args:
            session_id: 삭제할 세션 ID

        Returns:
            삭제 성공 여부
        """
        async for db_session in get_async_db():
            try:
                # 세션 삭제
                result = await db_session.execute(
                    delete(ChatSession).where(ChatSession.session_id == session_id)
                )
                await db_session.commit()

                if result.rowcount > 0:
                    logger.info(f"Session deleted: {session_id}")

                    # checkpoint 테이블들도 정리 (FK 없으므로 수동 삭제)
                    await self._delete_checkpoints(db_session, session_id)

                    return True
                else:
                    logger.warning(f"Session not found for deletion: {session_id}")
                    return False

            except Exception as e:
                await db_session.rollback()
                logger.error(f"Failed to delete session: {e}")
                return False
            finally:
                break

    async def _delete_checkpoints(self, db_session: AsyncSession, session_id: str):
        """
        체크포인트 관련 데이터 삭제

        Args:
            db_session: DB 세션
            session_id: 세션 ID
        """
        try:
            # checkpoints 테이블 정리
            await db_session.execute(
                "DELETE FROM checkpoints WHERE session_id = :session_id",
                {"session_id": session_id}
            )
            # checkpoint_writes 테이블 정리
            await db_session.execute(
                "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
                {"session_id": session_id}
            )
            # checkpoint_blobs 테이블 정리
            await db_session.execute(
                "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
                {"session_id": session_id}
            )
            await db_session.commit()
            logger.debug(f"Checkpoints deleted for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete checkpoints: {e}")

    async def cleanup_expired_sessions(self) -> int:
        """
        만료된 세션 정리 (24시간 이상 미활동)

        Returns:
            정리된 세션 수
        """
        async for db_session in get_async_db():
            try:
                # 24시간 전 시점
                cutoff_time = datetime.now(timezone.utc) - self.session_ttl

                # 만료된 세션 조회
                query = select(ChatSession.session_id).where(
                    ChatSession.updated_at < cutoff_time
                )
                result = await db_session.execute(query)
                expired_sessions = [row[0] for row in result]

                if expired_sessions:
                    # 세션 삭제
                    await db_session.execute(
                        delete(ChatSession).where(
                            ChatSession.session_id.in_(expired_sessions)
                        )
                    )

                    # 체크포인트도 삭제
                    for session_id in expired_sessions:
                        await self._delete_checkpoints(db_session, session_id)

                    await db_session.commit()

                    count = len(expired_sessions)
                    logger.info(f"Cleaned up {count} expired sessions")
                    return count

                return 0

            except Exception as e:
                await db_session.rollback()
                logger.error(f"Failed to cleanup sessions: {e}")
                return 0
            finally:
                break

    async def get_active_session_count(self) -> int:
        """
        활성 세션 수 조회

        Returns:
            현재 활성 세션 수
        """
        async for db_session in get_async_db():
            try:
                # 24시간 이내 활동 세션 카운트
                cutoff_time = datetime.now(timezone.utc) - self.session_ttl

                query = select(func.count()).select_from(ChatSession).where(
                    ChatSession.updated_at >= cutoff_time
                )
                result = await db_session.execute(query)
                count = result.scalar() or 0

                return count

            except Exception as e:
                logger.error(f"Failed to count sessions: {e}")
                return 0
            finally:
                break

    async def extend_session(self, session_id: str, hours: int = 24) -> bool:
        """
        세션 만료 시간 연장 (updated_at 갱신)

        Args:
            session_id: 연장할 세션 ID
            hours: 연장할 시간 (현재 미사용)

        Returns:
            연장 성공 여부
        """
        async for db_session in get_async_db():
            try:
                # updated_at 갱신
                result = await db_session.execute(
                    update(ChatSession)
                    .where(ChatSession.session_id == session_id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
                await db_session.commit()

                if result.rowcount > 0:
                    logger.info(f"Session extended: {session_id}")
                    return True

                return False

            except Exception as e:
                await db_session.rollback()
                logger.error(f"Failed to extend session: {e}")
                return False
            finally:
                break


# === 전역 싱글톤 ===

_session_manager: Optional[PostgreSQLSessionManager] = None


def get_postgres_session_manager() -> PostgreSQLSessionManager:
    """
    PostgreSQLSessionManager 싱글톤 반환

    FastAPI Depends()에서 사용

    Returns:
        PostgreSQLSessionManager 인스턴스
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = PostgreSQLSessionManager(session_ttl_hours=24)

    return _session_manager


def reset_postgres_session_manager():
    """
    SessionManager 초기화 (테스트용)
    """
    global _session_manager
    _session_manager = None


# === 호환성 레이어 (기존 코드 호환) ===

# 기존 SessionManager를 PostgreSQLSessionManager로 대체
SessionManager = PostgreSQLSessionManager
get_session_manager = get_postgres_session_manager