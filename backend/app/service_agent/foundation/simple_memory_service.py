"""
SimpleMemoryService - Memory 테이블 없이 chat_messages만 사용
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import tiktoken
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatMessage, ChatSession
from app.core.config import settings
from app.service_agent.llm_manager.llm_service import LLMService

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
        user_id: int,
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
        user_id: int,
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
        user_id: int,
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
        user_id: int
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
        user_id: int,
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
        user_id: int,
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

    # === 핵심 메모리 메서드 (Phase 1 구현) ===

    async def load_recent_memories(
        self,
        user_id: int,
        limit: int = 5,
        relevance_filter: str = "ALL",
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        최근 세션의 메모리 로드 (chat_sessions.session_metadata 기반)

        이 메서드는 Long-term Memory의 핵심으로, 사용자의 이전 대화 맥락을 로드합니다.
        user_id 기반으로 조회하므로 여러 대화창(세션) 간 메모리가 공유됩니다.

        메모리 공유 범위 (settings.MEMORY_LOAD_LIMIT로 제어):
            현재 구현은 "여러 대화창 간 메모리 공유" 방식입니다:
            - user_id 기반: 같은 유저의 모든 세션 검색
            - limit으로 범위 제어: 최근 N개 세션만 로드
            - session_id 제외: 현재 진행 중인 세션은 제외

        동작 방식:
            1. user_id로 모든 세션 조회 (같은 유저의 전체 대화 이력)
            2. session_id가 주어지면 해당 세션 제외 (불완전한 데이터 방지)
            3. metadata가 있는 세션만 필터링
            4. updated_at 기준 최신순 정렬
            5. limit 개수만큼만 로드

        메모리 범위 조정 방법:
            .env 파일에서 MEMORY_LOAD_LIMIT 값 변경:
            - 0  : 다른 세션 기억 안 함 (세션별 격리, 프라이버시 중요 시)
            - 1  : 최근 1개 세션만 기억 (최소 문맥)
            - 3  : 최근 3개 세션 기억 (균형)
            - 5  : 최근 5개 세션 기억 (기본값, 권장)
            - 10 : 최근 10개 세션 기억 (긴 기억, 장기 프로젝트)

        사용 예시:
            # 기본 사용 (최근 5개 세션)
            memories = await memory_service.load_recent_memories(
                user_id="1",
                session_id="current-session-123"
            )

            # 최근 3개만
            memories = await memory_service.load_recent_memories(
                user_id="1",
                limit=3,
                session_id="current-session-123"
            )

        Args:
            user_id: 사용자 ID (필수)
            limit: 조회할 세션 개수 (기본 5개, settings.MEMORY_LOAD_LIMIT)
            relevance_filter: 필터 옵션 (현재 미사용, 향후 확장용)
            session_id: 제외할 세션 ID (현재 진행 중인 세션, 선택적)

        Returns:
            메모리 리스트:
            [
                {
                    "session_id": "session-abc-123",
                    "summary": "강남구 아파트 전세 시세 문의 (5억~7억)",
                    "timestamp": "2025-10-20T14:30:00",
                    "title": "강남구 전세 시세"
                },
                ...
            ]

        Note:
            - 저장 위치: chat_sessions.session_metadata (JSONB)
            - 저장 키: conversation_summary
            - 저장 시점: 대화 완료 후 (save_conversation 메서드)
            - session_id가 None이면 모든 세션 포함 (주의: 현재 세션의 불완전한 데이터 포함 가능)
            - limit=0이면 빈 리스트 반환 (다른 세션 기억 안 함)

        See Also:
            - config.py: MEMORY_LOAD_LIMIT 설정
            - team_supervisor.py: 실제 호출 지점
            - reports/Manual/MEMORY_CONFIGURATION_GUIDE.md: 상세 설정 가이드
        """
        try:
            # 기본 쿼리: user_id와 metadata가 있는 세션만
            query = select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.session_metadata.isnot(None)
            )

            # 현재 진행 중인 세션 제외 (불완전한 데이터 방지)
            if session_id:
                query = query.where(ChatSession.session_id != session_id)

            # 최신순 정렬 및 개수 제한
            query = query.order_by(ChatSession.updated_at.desc()).limit(limit)

            result = await self.db.execute(query)
            sessions = result.scalars().all()

            # conversation_summary 추출
            memories = []
            for session in sessions:
                metadata = session.session_metadata
                if metadata and "conversation_summary" in metadata:
                    memories.append({
                        "session_id": session.session_id,
                        "summary": metadata["conversation_summary"],
                        "timestamp": session.updated_at.isoformat(),
                        "title": session.title
                    })

            logger.info(f"Loaded {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to load recent memories for user {user_id}: {e}")
            return []

    async def save_conversation(
        self,
        user_id: int,
        session_id: str,
        messages: List[dict],
        summary: str
    ) -> None:
        """
        대화 요약을 chat_sessions.session_metadata에 저장

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID (ChatSession.session_id)
            messages: 메시지 리스트 (개수 카운트용)
            summary: 대화 요약

        Note:
            - chat_sessions.session_metadata에 conversation_summary 저장
            - flag_modified로 JSONB 변경 추적
            - user_id 일치 확인으로 보안 강화
        """
        try:
            # 세션 조회 (user_id 일치 확인)
            query = select(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            )
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(
                    f"Session not found or user mismatch: "
                    f"session_id={session_id}, user_id={user_id}"
                )
                return

            # metadata 초기화 (없는 경우)
            if session.session_metadata is None:
                session.session_metadata = {}

            # conversation_summary 저장
            session.session_metadata["conversation_summary"] = summary
            session.session_metadata["last_updated"] = datetime.now().isoformat()
            session.session_metadata["message_count"] = len(messages)

            # JSONB 변경 플래그 설정
            flag_modified(session, "session_metadata")

            await self.db.commit()
            logger.info(f"Conversation saved: session_id={session_id}, summary_length={len(summary)}")

        except Exception as e:
            logger.error(f"Failed to save conversation for session {session_id}: {e}")
            await self.db.rollback()
            raise

    # === 3-Tier Memory 메서드 (Phase 1 구현) ===

    async def load_tiered_memories(
        self,
        user_id: int,
        current_session_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        3-Tier Hybrid Memory 로드

        1-5 세션: 전체 메시지
        6-10 세션: LLM 요약
        11-20 세션: LLM 요약

        Args:
            user_id: 사용자 ID
            current_session_id: 현재 세션 ID (제외할 세션)

        Returns:
            {
                "shortterm": [...],  # 1-5 세션 전체 메시지
                "midterm": [...],    # 6-10 세션 요약
                "longterm": [...]    # 11-20 세션 요약
            }
        """
        try:
            # 토큰 카운팅 준비
            encoding = tiktoken.get_encoding("cl100k_base")
            total_tokens = 0

            # 결과 구조
            tiered_memories = {
                "shortterm": [],
                "midterm": [],
                "longterm": []
            }

            # 전체 세션 조회 (최신순)
            total_limit = (
                settings.SHORTTERM_MEMORY_LIMIT +
                settings.MIDTERM_MEMORY_LIMIT +
                settings.LONGTERM_MEMORY_LIMIT
            )

            query = select(ChatSession).where(
                ChatSession.user_id == user_id
            )

            if current_session_id:
                query = query.where(ChatSession.session_id != current_session_id)

            query = query.order_by(ChatSession.updated_at.desc()).limit(total_limit)

            result = await self.db.execute(query)
            sessions = result.scalars().all()

            # 세션별 처리
            for idx, session in enumerate(sessions):
                # 토큰 제한 체크
                if total_tokens >= settings.MEMORY_TOKEN_LIMIT:
                    logger.info(f"Token limit reached: {total_tokens}")
                    break

                if idx < settings.SHORTTERM_MEMORY_LIMIT:
                    # Short-term: 전체 메시지
                    messages_query = select(ChatMessage).where(
                        ChatMessage.session_id == session.session_id
                    ).order_by(ChatMessage.created_at).limit(settings.MEMORY_MESSAGE_LIMIT)

                    messages_result = await self.db.execute(messages_query)
                    messages = messages_result.scalars().all()

                    messages_list = [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]

                    # 토큰 계산
                    content_text = " ".join([m["content"] for m in messages_list])
                    tokens = len(encoding.encode(content_text))
                    total_tokens += tokens

                    if total_tokens > settings.MEMORY_TOKEN_LIMIT:
                        break

                    tiered_memories["shortterm"].append({
                        "session_id": session.session_id,
                        "messages": messages_list,
                        "metadata": session.session_metadata,
                        "tier": "shortterm",
                        "timestamp": session.updated_at.isoformat()
                    })

                elif idx < settings.SHORTTERM_MEMORY_LIMIT + settings.MIDTERM_MEMORY_LIMIT:
                    # Mid-term: 요약
                    summary = await self._get_or_create_summary(session)

                    tokens = len(encoding.encode(summary))
                    total_tokens += tokens

                    if total_tokens > settings.MEMORY_TOKEN_LIMIT:
                        break

                    tiered_memories["midterm"].append({
                        "session_id": session.session_id,
                        "summary": summary,
                        "metadata": session.session_metadata,
                        "tier": "midterm",
                        "timestamp": session.updated_at.isoformat()
                    })

                else:
                    # Long-term: 요약
                    summary = await self._get_or_create_summary(session)

                    tokens = len(encoding.encode(summary))
                    total_tokens += tokens

                    if total_tokens > settings.MEMORY_TOKEN_LIMIT:
                        break

                    tiered_memories["longterm"].append({
                        "session_id": session.session_id,
                        "summary": summary,
                        "metadata": session.session_metadata,
                        "tier": "longterm",
                        "timestamp": session.updated_at.isoformat()
                    })

            logger.info(
                f"Loaded tiered memories - Tokens: {total_tokens}, "
                f"Short: {len(tiered_memories['shortterm'])}, "
                f"Mid: {len(tiered_memories['midterm'])}, "
                f"Long: {len(tiered_memories['longterm'])}"
            )

            return tiered_memories

        except Exception as e:
            logger.error(f"Failed to load tiered memories: {e}")
            return {"shortterm": [], "midterm": [], "longterm": []}

    async def _get_or_create_summary(self, session: ChatSession) -> str:
        """요약 캐시 조회 또는 생성"""
        metadata = session.session_metadata

        if metadata and "conversation_summary" in metadata:
            return metadata["conversation_summary"]

        # 요약 없으면 LLM으로 생성
        summary = await self.summarize_with_llm(session.session_id)

        # 캐시 저장
        await self._save_summary_to_metadata(session.session_id, summary)

        return summary

    async def summarize_with_llm(self, session_id: str) -> str:
        """LLM으로 대화 요약 생성"""
        try:
            # 메시지 로드
            messages_query = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at).limit(settings.MEMORY_MESSAGE_LIMIT)

            result = await self.db.execute(messages_query)
            messages = result.scalars().all()

            if not messages:
                return "대화 없음"

            # 대화 포맷팅
            conversation_text = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in messages
            ])

            # LLM 호출
            llm_service = LLMService()
            summary = await llm_service.complete_async(
                prompt_name="conversation_summary",
                variables={
                    "conversation": conversation_text,
                    "max_length": settings.SUMMARY_MAX_LENGTH
                },
                temperature=0.3,
                max_tokens=150
            )

            logger.info(f"LLM summarization completed: {summary[:50]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            # Fallback: 마지막 메시지 잘라내기
            if messages:
                return messages[-1].content[:settings.SUMMARY_MAX_LENGTH]
            return "요약 생성 실패"

    async def _save_summary_to_metadata(self, session_id: str, summary: str) -> None:
        """JSONB에 요약 저장"""
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return

            if session.session_metadata is None:
                session.session_metadata = {}

            session.session_metadata["conversation_summary"] = summary
            session.session_metadata["summary_method"] = "llm"
            session.session_metadata["summary_updated_at"] = datetime.now().isoformat()

            flag_modified(session, "session_metadata")
            await self.db.commit()

            logger.info(f"Summary saved for session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            await self.db.rollback()

    async def summarize_conversation_background(
        self,
        session_id: str,
        user_id: int,
        messages: List[Dict[str, Any]]
    ) -> None:
        """백그라운드에서 대화 요약 (fire-and-forget)"""
        asyncio.create_task(
            self._background_summary_with_new_session(session_id, user_id)
        )
        logger.info(f"Background summary task created for session: {session_id}")

    async def _background_summary_with_new_session(
        self,
        session_id: str,
        user_id: int
    ) -> None:
        """독립 세션으로 백그라운드 요약"""
        try:
            from app.db.postgre_db import get_async_db

            async for db_session in get_async_db():
                temp_service = SimpleMemoryService(db_session)
                summary = await temp_service.summarize_with_llm(session_id)
                await temp_service._save_summary_to_metadata(session_id, summary)
                break

        except Exception as e:
            logger.error(f"Background summary failed for session {session_id}: {e}")


# === 호환성 레이어 (기존 코드 호환) ===

# 기존 LongTermMemoryService를 SimpleMemoryService로 대체
LongTermMemoryService = SimpleMemoryService