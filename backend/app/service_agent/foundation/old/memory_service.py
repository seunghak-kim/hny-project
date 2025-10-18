"""
Long-term Memory Service

사용자의 대화 기록, 선호도, 엔티티 추적을 관리하는 서비스
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime
import logging

from app.models.memory import ConversationMemory, UserPreference, EntityMemory
from app.models.users import User

logger = logging.getLogger(__name__)


class LongTermMemoryService:
    """Long-term Memory 관리 서비스"""

    def __init__(self, db_session: AsyncSession):
        """
        Args:
            db_session: SQLAlchemy AsyncSession
        """
        self.db = db_session

    async def load_recent_memories(
        self,
        user_id: int,
        limit: int = 5,
        relevance_filter: Optional[str] = "RELEVANT"
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 기록 로드

        Args:
            user_id: 사용자 ID
            limit: 로드할 대화 개수 (기본 5개)
            relevance_filter: 관련성 필터 ("RELEVANT", "IRRELEVANT", None=모두)

        Returns:
            List[Dict]: 대화 기록 리스트
        """
        try:
            query = select(ConversationMemory).where(
                ConversationMemory.user_id == user_id
            )

            # 관련성 필터 적용
            if relevance_filter:
                query = query.where(ConversationMemory.relevance == relevance_filter)

            # 최신순 정렬 및 제한
            query = query.order_by(desc(ConversationMemory.created_at)).limit(limit)

            result = await self.db.execute(query)
            memories = result.scalars().all()

            # Dict 형식으로 변환
            return [
                {
                    "id": str(memory.id),
                    "query": memory.query,
                    "response_summary": memory.response_summary,
                    "relevance": memory.relevance,
                    "intent_detected": memory.intent_detected,
                    "entities_mentioned": memory.entities_mentioned,
                    "created_at": memory.created_at.isoformat(),
                    "conversation_metadata": memory.conversation_metadata
                }
                for memory in memories
            ]

        except Exception as e:
            logger.error(f"Failed to load recent memories for user {user_id}: {e}")
            return []

    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        사용자 선호도 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 사용자 선호도 (없으면 빈 dict)
        """
        try:
            query = select(UserPreference).where(UserPreference.user_id == user_id)
            result = await self.db.execute(query)
            preference = result.scalar_one_or_none()

            if preference:
                return preference.preferences or {}
            else:
                return {}

        except Exception as e:
            logger.error(f"Failed to get user preferences for user {user_id}: {e}")
            return {}

    async def save_conversation(
        self,
        user_id: int,
        query: str,
        response_summary: str,
        relevance: str,
        session_id: Optional[str] = None,
        intent_detected: Optional[str] = None,
        entities_mentioned: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        대화 기록 저장

        Args:
            user_id: 사용자 ID
            query: 사용자 쿼리
            response_summary: 응답 요약 (100-200자 정도)
            relevance: 관련성 ("RELEVANT" or "IRRELEVANT")
            session_id: 채팅 세션 ID (Chat History & State Endpoints)
            intent_detected: 감지된 의도
            entities_mentioned: 언급된 엔티티 (JSONB)
            conversation_metadata: 추가 메타데이터 (teams_used, response_time 등)

        Returns:
            bool: 저장 성공 여부
        """
        try:
            new_memory = ConversationMemory(
                user_id=user_id,
                query=query,
                response_summary=response_summary,
                relevance=relevance,
                session_id=session_id,
                intent_detected=intent_detected,
                entities_mentioned=entities_mentioned,
                conversation_metadata=conversation_metadata
            )

            self.db.add(new_memory)
            await self.db.commit()

            logger.info(f"Saved conversation memory for user {user_id}")

            # 엔티티 추적 업데이트 (비동기)
            if entities_mentioned:
                await self._update_entity_tracking(user_id, entities_mentioned)

            return True

        except Exception as e:
            logger.error(f"Failed to save conversation for user {user_id}: {e}")
            await self.db.rollback()
            return False

    async def update_user_preferences(
        self,
        user_id: int,
        preferences_update: Dict[str, Any]
    ) -> bool:
        """
        사용자 선호도 업데이트 (병합 방식)

        Args:
            user_id: 사용자 ID
            preferences_update: 업데이트할 선호도 데이터

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 기존 선호도 조회
            query = select(UserPreference).where(UserPreference.user_id == user_id)
            result = await self.db.execute(query)
            preference = result.scalar_one_or_none()

            if preference:
                # 기존 선호도 병합
                current_prefs = preference.preferences or {}
                current_prefs.update(preferences_update)
                preference.preferences = current_prefs
                preference.updated_at = datetime.utcnow()
            else:
                # 새로운 선호도 생성
                preference = UserPreference(
                    user_id=user_id,
                    preferences=preferences_update
                )
                self.db.add(preference)

            await self.db.commit()
            logger.info(f"Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update preferences for user {user_id}: {e}")
            await self.db.rollback()
            return False

    async def _update_entity_tracking(
        self,
        user_id: int,
        entities_mentioned: Dict[str, Any]
    ):
        """
        엔티티 추적 업데이트 (내부 메서드)

        entities_mentioned 형식 예시:
        {
            "properties": [{"id": "prop123", "name": "강남 아파트"}],
            "regions": [{"id": "gangnam", "name": "강남구"}],
            "agents": [{"id": "agent456", "name": "김중개"}]
        }

        Args:
            user_id: 사용자 ID
            entities_mentioned: 언급된 엔티티
        """
        try:
            for entity_type, entities in entities_mentioned.items():
                if not isinstance(entities, list):
                    continue

                for entity in entities:
                    entity_id = entity.get("id")
                    entity_name = entity.get("name")

                    if not entity_id:
                        continue

                    # 기존 엔티티 조회
                    query = select(EntityMemory).where(
                        EntityMemory.user_id == user_id,
                        EntityMemory.entity_type == entity_type,
                        EntityMemory.entity_id == entity_id
                    )
                    result = await self.db.execute(query)
                    entity_mem = result.scalar_one_or_none()

                    if entity_mem:
                        # 기존 엔티티 업데이트 (mention_count 증가)
                        entity_mem.mention_count += 1
                        entity_mem.last_mentioned_at = datetime.utcnow()
                    else:
                        # 새 엔티티 생성
                        entity_mem = EntityMemory(
                            user_id=user_id,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_name=entity_name,
                            mention_count=1
                        )
                        self.db.add(entity_mem)

            await self.db.commit()
            logger.debug(f"Updated entity tracking for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update entity tracking for user {user_id}: {e}")
            await self.db.rollback()

    async def get_entity_history(
        self,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        사용자의 엔티티 기록 조회 (추가 기능)

        Args:
            user_id: 사용자 ID
            entity_type: 엔티티 타입 필터 (None=모두)
            limit: 조회 개수

        Returns:
            List[Dict]: 엔티티 기록
        """
        try:
            query = select(EntityMemory).where(EntityMemory.user_id == user_id)

            if entity_type:
                query = query.where(EntityMemory.entity_type == entity_type)

            query = query.order_by(desc(EntityMemory.last_mentioned_at)).limit(limit)

            result = await self.db.execute(query)
            entities = result.scalars().all()

            return [
                {
                    "id": str(entity.id),
                    "entity_type": entity.entity_type,
                    "entity_id": entity.entity_id,
                    "entity_name": entity.entity_name,
                    "mention_count": entity.mention_count,
                    "first_mentioned_at": entity.first_mentioned_at.isoformat(),
                    "last_mentioned_at": entity.last_mentioned_at.isoformat(),
                    "entity_context": entity.entity_context
                }
                for entity in entities
            ]

        except Exception as e:
            logger.error(f"Failed to get entity history for user {user_id}: {e}")
            return []
