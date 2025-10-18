"""
Chat API Router
FastAPI WebSocket endpoints for real-time chat with service_agent integration
user_id = 1 (임시 하드코딩)
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone
import logging
import asyncio
import json
from sqlalchemy import func

from app.api.schemas import (
    SessionStartRequest, SessionStartResponse,
    SessionInfo, DeleteSessionResponse,
    ErrorResponse
)
from app.api.postgres_session_manager import get_session_manager, SessionManager
from app.api.ws_manager import get_connection_manager, ConnectionManager
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# ============================================================================
# Helper Functions
# ============================================================================

async def _save_message_to_db(session_id: str, role: str, content: str, structured_data: dict = None) -> bool:
    """
    chat_messages 테이블에 메시지 저장

    Args:
        session_id: WebSocket session ID (NOT chat_session_id!)
        role: 'user' or 'assistant'
        content: 메시지 내용
        structured_data: 구조화된 답변 데이터 (sections, metadata 등)

    Returns:
        bool: 저장 성공 여부
    """
    result = False
    async for db in get_async_db():
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                structured_data=structured_data  # ✅ 추가
            )
            db.add(message)
            await db.commit()
            logger.info(f"💾 Message saved: {role} → {session_id[:20]}... (structured: {structured_data is not None})")
            result = True
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Failed to save message: {e}")
            result = False
        finally:
            break

    return result


# ============================================================================
# Supervisor Singleton Pattern
# ============================================================================

_supervisor_instance = None
_supervisor_lock = asyncio.Lock()


async def get_supervisor(enable_checkpointing: bool = True) -> TeamBasedSupervisor:
    """
    Supervisor 싱글톤 인스턴스 반환

    Args:
        enable_checkpointing: Checkpointing 활성화 여부

    Returns:
        TeamBasedSupervisor: 싱글톤 인스턴스
    """
    global _supervisor_instance

    async with _supervisor_lock:
        if _supervisor_instance is None:
            logger.info("🚀 Creating singleton TeamBasedSupervisor instance...")

            from app.service_agent.foundation.context import create_default_llm_context
            llm_context = create_default_llm_context()

            _supervisor_instance = TeamBasedSupervisor(
                llm_context=llm_context,
                enable_checkpointing=enable_checkpointing
            )

            logger.info("✅ Singleton TeamBasedSupervisor created successfully")

        return _supervisor_instance


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest = SessionStartRequest(),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    새 채팅 세션 시작

    서버가 고유한 UUID 기반 session_id 생성

    Args:
        request: 세션 시작 요청 (선택적 필드)

    Returns:
        SessionStartResponse: 생성된 세션 정보
    """
    try:
        session_id, expires_at = await session_mgr.create_session(
            user_id=request.user_id,
            metadata=request.metadata
        )

        # ✅ chat_sessions 테이블에도 저장 (DB 영속성)
        async for db in get_async_db():
            try:
                # 이미 존재하는지 확인
                existing_session_query = select(ChatSession).where(ChatSession.session_id == session_id)
                result = await db.execute(existing_session_query)
                existing_session = result.scalar_one_or_none()

                if not existing_session:
                    # 새 세션 추가
                    new_chat_session = ChatSession(
                        session_id=session_id,
                        user_id=request.user_id or 1,
                        title="새 대화"
                    )
                    db.add(new_chat_session)
                    await db.commit()
                    logger.info(f"✅ Session saved to chat_sessions table: {session_id}")
                else:
                    logger.info(f"Session already exists in chat_sessions: {session_id}")
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Failed to save session to chat_sessions: {db_error}")
            finally:
                break

        logger.info(
            f"New session created: {session_id} "
            f"(user: {request.user_id or 'anonymous'})"
        )

        return SessionStartResponse(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )




# ============================================================================
# Chat History & State Endpoints (for Frontend)
# ============================================================================

from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import select, update, delete, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import get_async_db
from app.models.chat import ChatSession, ChatMessage
import uuid


class ChatSessionCreate(BaseModel):
    """채팅 세션 생성 요청"""
    title: Optional[str] = "새 대화"
    metadata: Optional[dict] = None


class ChatSessionUpdate(BaseModel):
    """채팅 세션 업데이트 요청"""
    title: str


class ChatSessionResponse(BaseModel):
    """채팅 세션 응답"""
    id: str
    title: str
    created_at: str
    updated_at: str
    last_message: Optional[str] = None
    message_count: int = 0


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    id: int
    role: str
    content: str
    structured_data: Optional[dict] = None  # ✅ 추가
    created_at: str


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db)
):
    """
    사용자의 채팅 세션 목록 조회 (Chat History & State Endpoints)
    Args:
        limit: 조회할 세션 수 (최대 50)
        offset: 페이지네이션 오프셋

    Returns:
        List[ChatSessionResponse]: 채팅 세션 목록
    """
    try:
        user_id = 1  # 임시 하드코딩

        # 세션 목록 조회
        query = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        sessions = result.scalars().all()

        # 각 세션의 마지막 메시지 조회
        response_sessions = []
        for session in sessions:
            # 마지막 메시지 조회
            last_msg_query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session.session_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(1)
            )
            last_msg_result = await db.execute(last_msg_query)
            last_message = last_msg_result.scalar_one_or_none()

            # 메시지 수 조회
            count_query = select(func.count()).select_from(ChatMessage).where(
                ChatMessage.session_id == session.session_id
            )
            count_result = await db.execute(count_query)
            message_count = count_result.scalar() or 0

            response_sessions.append(ChatSessionResponse(
                id=session.session_id,
                title=session.title,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                last_message=last_message.content[:100] if last_message else None,
                message_count=message_count
            ))

        return response_sessions

    except Exception as e:
        logger.error(f"Failed to fetch chat sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate = ChatSessionCreate(),
    db: AsyncSession = Depends(get_async_db)
):
    """
    새 채팅 세션 생성 (Chat History & State Endpoints)

    Args:
        request: 세션 생성 요청

    Returns:
        ChatSessionResponse: 생성된 세션 정보
    """
    try:
        user_id = 1  # 임시 하드코딩
        session_id = f"session-{uuid.uuid4()}"  # ✅ 스키마 표준 형식으로 수정

        # 새 세션 생성
        new_session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            title=request.title
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        logger.info(f"Chat session created: {session_id}")

        return ChatSessionResponse(
            id=new_session.session_id,
            title=new_session.title,
            created_at=new_session.created_at.isoformat(),
            updated_at=new_session.updated_at.isoformat(),
            last_message=None,
            message_count=0
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db)
):
    """
    특정 세션의 메시지 목록 조회

    Args:
        session_id: 채팅 세션 ID
        limit: 조회할 메시지 수
        offset: 페이지네이션 오프셋

    Returns:
        List[ChatMessageResponse]: 메시지 목록
    """
    try:
        # 세션 존재 확인
        session_query = select(ChatSession).where(ChatSession.session_id == session_id)
        session_result = await db.execute(session_query)
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 메시지 조회
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        messages = result.scalars().all()

        return [
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                structured_data=msg.structured_data,  # ✅ 추가
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    request: ChatSessionUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    채팅 세션 제목 업데이트

    Args:
        session_id: 채팅 세션 ID
        request: 업데이트 요청

    Returns:
        ChatSessionResponse: 업데이트된 세션 정보
    """
    try:
        # 세션 조회
        query = select(ChatSession).where(ChatSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 제목 업데이트
        session.title = request.title
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

        # 마지막 메시지 조회
        last_msg_query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_query)
        last_message = last_msg_result.scalar_one_or_none()

        # 메시지 수 조회
        count_query = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.session_id == session_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        logger.info(f"Chat session updated: {session_id}")

        return ChatSessionResponse(
            id=session.session_id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            last_message=last_message.content[:100] if last_message else None,
            message_count=message_count
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update session")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    hard_delete: bool = False,
    db: AsyncSession = Depends(get_async_db)
):
    """
    채팅 세션 삭제

    Args:
        session_id: 채팅 세션 ID
        hard_delete: 완전 삭제 여부 (True: DB에서 삭제, False: 소프트 삭제)

    Returns:
        dict: 삭제 결과
    """
    try:
        # 세션 조회
        query = select(ChatSession).where(ChatSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if hard_delete:
            # 하드 삭제 (CASCADE로 messages도 자동 삭제)
            await db.delete(session)

            # checkpoints 관련 테이블도 정리
            await db.execute(
                "DELETE FROM checkpoints WHERE session_id = :session_id",
                {"session_id": session_id}
            )
            await db.execute(
                "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
                {"session_id": session_id}
            )
            await db.execute(
                "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
                {"session_id": session_id}
            )

            await db.commit()
            logger.info(f"Chat session hard deleted: {session_id}")

            return {
                "message": "Session permanently deleted",
                "session_id": session_id,
                "deleted_at": datetime.now().isoformat()
            }
        else:
            # 소프트 삭제 (제목만 변경)
            session.title = f"[삭제됨] {session.title}"
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Chat session soft deleted: {session_id}")

            return {
                "message": "Session marked as deleted",
                "session_id": session_id,
                "deleted_at": datetime.now().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    세션 정보 조회

    Args:
        session_id: 조회할 세션 ID

    Returns:
        SessionInfo: 세션 정보
    """
    session = await session_mgr.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or expired: {session_id}"
        )

    return SessionInfo(
        session_id=session["session_id"],
        created_at=session["created_at"].isoformat(),
        expires_at=session["expires_at"].isoformat(),
        last_activity=session["last_activity"].isoformat(),
        metadata=session.get("metadata", {})
    )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """
    세션 삭제 (로그아웃)

    Args:
        session_id: 삭제할 세션 ID

    Returns:
        DeleteSessionResponse: 삭제 결과
    """
    success = await session_mgr.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    # WebSocket 연결도 정리
    conn_mgr.cleanup_session(session_id)

    logger.info(f"Session deleted: {session_id}")

    return DeleteSessionResponse(
        message="Session deleted successfully",
        session_id=session_id
    )


# ============================================================================
# WebSocket Chat Endpoint
# ============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """
    실시간 채팅 WebSocket 엔드포인트

    Protocol:
        Client → Server:
            - {"type": "query", "query": "...", "enable_checkpointing": true}
            - {"type": "interrupt_response", "action": "approve|modify", "modified_todos": [...]}
            - {"type": "todo_skip", "todo_id": "..."}

        Server → Client:
            - {"type": "connected", "session_id": "..."}
            - {"type": "planning_start", "message": "계획을 수립하고 있습니다..."}
            - {"type": "plan_ready", "intent": "...", "execution_steps": [...], "estimated_total_time": ..., "keywords": [...]}
            - {"type": "execution_start", "message": "작업 실행을 시작합니다...", "execution_steps": [...]}
            - {"type": "todo_created", "execution_steps": [...]}
            - {"type": "todo_updated", "execution_steps": [...]}
            - {"type": "step_start", "agent": "...", "task": "..."}
            - {"type": "step_progress", "agent": "...", "progress": 50}
            - {"type": "step_complete", "agent": "...", "result": {...}}
            - {"type": "final_response", "response": {...}}
            - {"type": "error", "error": "...", "details": {...}}

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID
    """
    # 1. 세션 검증
    logger.info(f"🔍 Validating WebSocket session: {session_id}")

    validation_result = await session_mgr.validate_session(session_id)
    logger.info(f"🔍 Validation result: {validation_result}")

    if not validation_result:
        await websocket.close(code=4004, reason="Session not found or expired")
        logger.warning(f"WebSocket rejected: invalid session {session_id}")
        return

    logger.info(f"✅ Session validated: {session_id}")

    # 2. WebSocket 연결
    await conn_mgr.connect(session_id, websocket)

    # 3. 연결 확인 메시지
    await conn_mgr.send_message(session_id, {
        "type": "connected",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    })

    # 4. Supervisor 인스턴스 가져오기
    supervisor = await get_supervisor(enable_checkpointing=True)

    try:
        # 5. 메시지 수신 루프
        while True:
            try:
                # 메시지 수신 (JSON)
                data = await websocket.receive_json()
                message_type = data.get("type")

                logger.info(f"📥 Received from {session_id}: {message_type}")

                # === Query 처리 ===
                if message_type == "query":
                    query = data.get("query")
                    enable_checkpointing = data.get("enable_checkpointing", True)

                    if not query:
                        await conn_mgr.send_message(session_id, {
                            "type": "error",
                            "error": "Query cannot be empty",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue

                    # Progress callback 정의
                    async def progress_callback(event_type: str, event_data: dict):
                        """실시간 진행 상황 전송"""
                        await conn_mgr.send_message(session_id, {
                            "type": event_type,
                            **event_data,
                            "timestamp": datetime.now().isoformat()
                        })

                    # 비동기 쿼리 처리 시작
                    asyncio.create_task(
                        _process_query_async(
                            supervisor=supervisor,
                            query=query,
                            session_id=session_id,
                            enable_checkpointing=enable_checkpointing,
                            progress_callback=progress_callback,
                            conn_mgr=conn_mgr,
                            session_mgr=session_mgr
                        )
                    )

                # === Interrupt Response (계획 승인/수정) ===
                elif message_type == "interrupt_response":
                    # TODO: LangGraph interrupt 처리 (추후 구현)
                    action = data.get("action")  # "approve" or "modify"
                    modified_todos = data.get("modified_todos", [])

                    logger.info(f"Interrupt response: {action}")
                    # 현재는 로그만, 추후 LangGraph Command로 전달

                # === Todo Skip (실행 중 작업 건너뛰기) ===
                elif message_type == "todo_skip":
                    todo_id = data.get("todo_id")
                    logger.info(f"Todo skip requested: {todo_id}")
                    # TODO: 추후 구현

                # === 알 수 없는 메시지 ===
                else:
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    })

            except json.JSONDecodeError:
                await conn_mgr.send_message(session_id, {
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

    finally:
        # 6. 연결 해제
        conn_mgr.disconnect(session_id)
        logger.info(f"WebSocket closed: {session_id}")


async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager,
    session_mgr: SessionManager
):
    """
    비동기로 쿼리 처리 (백그라운드 태스크)

    Args:
        supervisor: TeamBasedSupervisor 인스턴스
        query: 사용자 질문
        session_id: 세션 ID (HTTP/WebSocket)
        enable_checkpointing: Checkpoint 활성화 여부
        progress_callback: 진행 상황 콜백
        conn_mgr: ConnectionManager
        session_mgr: SessionManager (user_id 추출용)
    """
    try:
        logger.info(f"Processing query for {session_id}: {query[:100]}...")

        # 💾 사용자 메시지 저장
        await _save_message_to_db(session_id, "user", query)

        # 세션에서 user_id 추출 (Long-term Memory용)
        user_id = 1  # 🔧 임시: 테스트용 하드코딩
        session_data = await session_mgr.get_session(session_id)
        if session_data:
            if user_id:
                logger.info(f"User ID {user_id} extracted from session {session_id}")

        # Streaming 방식으로 쿼리 처리
        result = await supervisor.process_query_streaming(
            query=query,
            session_id=session_id,
            user_id=user_id,
            progress_callback=progress_callback
        )

        # 최종 응답 전송
        # final_response만 추출 (result에는 datetime 필드가 있어 JSON 직렬화 불가)
        final_response = result.get("final_response", {})

        await conn_mgr.send_message(session_id, {
            "type": "final_response",
            "response": final_response,
            "timestamp": datetime.now().isoformat()
        })

        # 💾 AI 응답 저장
        response_content = (
            final_response.get("answer") or
            final_response.get("content") or
            final_response.get("message") or
            ""
        )
        # structured_data 추출
        structured_data = final_response.get("structured_data")

        if response_content:
            await _save_message_to_db(session_id, "assistant", response_content, structured_data)

        logger.info(f"Query completed for {session_id}")

    except Exception as e:
        logger.error(f"Query processing failed for {session_id}: {e}", exc_info=True)

        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": "Query processing failed",
            "details": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        })


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/stats/sessions")
async def get_session_stats(
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """세션 통계 조회"""
    active_count = await session_mgr.get_active_session_count()

    return {
        "active_sessions": active_count,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats/websockets")
async def get_websocket_stats(
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """WebSocket 연결 통계 조회"""
    return {
        "active_connections": conn_mgr.get_active_count(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/cleanup/sessions")
async def cleanup_expired_sessions(
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """만료된 세션 정리"""
    cleaned = await session_mgr.cleanup_expired_sessions()

    logger.info(f"Cleaned up {cleaned} expired sessions")

    return {
        "cleaned_sessions": cleaned,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Memory History Endpoints
# ============================================================================

@router.get("/memory/history")
async def get_memory_history(
    limit: int = 10
):
    """
    사용자의 대화 기록 조회 (Long-term Memory)

    Args:
        limit: 조회할 대화 개수 (기본 10개)

    Returns:
        List[Dict]: 대화 기록 리스트
    """
    try:
        # TODO: 실제 로그인 구현 후 session에서 user_id 추출
        user_id = 1  # 🔧 임시: 테스트용 하드코딩

        from app.db.postgre_db import get_async_db
        from app.service_agent.foundation.simple_memory_service import SimpleMemoryService

        async for db_session in get_async_db():
            memory_service = SimpleMemoryService(db_session)

            # 최근 메모리 조회 (호환성 메서드)
            memories = await memory_service.get_recent_memories(
                user_id=user_id,
                limit=limit
            )

            return {
                "user_id": user_id,
                "count": len(memories),
                "memories": memories,
                "timestamp": datetime.now().isoformat()
            }

        # generator가 비어있는 경우 (발생하지 않아야 함)
        raise HTTPException(status_code=500, detail="Failed to get database session")

    except Exception as e:
        logger.error(f"Failed to fetch memory history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch memory history: {str(e)}"
        )

