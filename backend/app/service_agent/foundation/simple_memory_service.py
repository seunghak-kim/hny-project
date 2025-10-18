"""
SimpleMemoryService - Memory 테이블 없이 chat_messages만 사용
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class SimpleMemoryService:
    """
    간단한 메모리 서비스 (chat_messages 기반)

    Note:
        - ConversationMemory/EntityMemory/UserPreference 제거됨
        - chat_messages만 사용
        - 메타데이터 추적 기능 제한적
    """

    def __init__(self, db_session: AsyncSession):
        """
        초기화

        Args:
            db_session: 비동기 DB 세션
        """
        self.db = db_session

    async def load_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 메시지 로드 (chat_messages 테이블)

        Args:
            session_id: 채팅 세션 ID
            limit: 조회 개수

        Returns:
            메시지 리스트
        """
        try:
            query = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at).limit(limit)

            result = await self.db.execute(query)
            messages = result.scalars().all()

            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error loading recent messages: {e}")
            return []

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> str:
        """
        대화 히스토리를 텍스트로 변환

        Args:
            session_id: 채팅 세션 ID
            limit: 조회 개수

        Returns:
            포맷팅된 대화 히스토리 문자열
        """
        messages = await self.load_recent_messages(session_id, limit)

        if not messages:
            return "No conversation history available."

        history_lines = []
        for msg in messages:
            history_lines.append(f"{msg['role']}: {msg['content']}")

        return "\n".join(history_lines)

    # === 호환성 메서드 (기존 LongTermMemoryService와 부분 호환) ===

    async def save_conversation_memory(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        대화 메모리 저장 (호환성용 - 실제로는 아무것도 안함)

        Note:
            - 이 메서드는 기존 코드 호환성을 위해 존재
            - 실제 저장은 chat_messages에 자동으로 됨
            - ConversationMemory 테이블이 없으므로 메타데이터 저장 안됨

        Returns:
            항상 True (호환성을 위해)
        """
        logger.debug(
            f"save_conversation_memory called (no-op): "
            f"session_id={session_id}, user_id={user_id}"
        )
        return True

    async def get_recent_memories(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        최근 메모리 조회 (호환성용 - 빈 리스트 반환)

        Note:
            - ConversationMemory 테이블이 없으므로 빈 리스트 반환
            - 필요시 chat_messages에서 조회하도록 수정 가능

        Returns:
            빈 리스트
        """
        logger.debug(f"get_recent_memories called (returns empty): user_id={user_id}")
        return []

    async def update_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        사용자 선호도 업데이트 (호환성용 - 아무것도 안함)

        Note:
            - UserPreference 테이블이 없으므로 저장 안됨

        Returns:
            항상 True (호환성을 위해)
        """
        logger.debug(f"update_user_preference called (no-op): user_id={user_id}, {key}={value}")
        return True

    async def get_user_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 선호도 조회 (호환성용 - 빈 dict 반환)

        Note:
            - UserPreference 테이블이 없으므로 빈 dict 반환

        Returns:
            빈 dictionary
        """
        logger.debug(f"get_user_preferences called (returns empty): user_id={user_id}")
        return {}

    async def save_entity_memory(
        self,
        user_id: str,
        entity_type: str,
        entity_name: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        엔티티 메모리 저장 (호환성용 - 아무것도 안함)

        Note:
            - EntityMemory 테이블이 없으므로 저장 안됨

        Returns:
            항상 True (호환성을 위해)
        """
        logger.debug(
            f"save_entity_memory called (no-op): "
            f"user_id={user_id}, entity={entity_type}/{entity_name}"
        )
        return True

    async def get_entity_memories(
        self,
        user_id: str,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        엔티티 메모리 조회 (호환성용 - 빈 리스트 반환)

        Note:
            - EntityMemory 테이블이 없으므로 빈 리스트 반환

        Returns:
            빈 리스트
        """
        logger.debug(f"get_entity_memories called (returns empty): user_id={user_id}")
        return []


# === 호환성 레이어 (기존 코드 호환) ===

# 기존 LongTermMemoryService를 SimpleMemoryService로 대체
LongTermMemoryService = SimpleMemoryService