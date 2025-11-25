"""
WebSocket Connection Manager
Real-time communication with message queuing and reconnection support
"""

import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 연결 관리자

    Features:
    - Session ID 기반 연결 관리
    - 메시지 큐잉 (연결 끊김 시 메시지 보존)
    - 재연결 시 큐잉된 메시지 전송
    """

    def __init__(self):
        # Active WebSocket connections: session_id → WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Message queues for disconnected sessions: session_id → asyncio.Queue
        self.message_queues: Dict[str, asyncio.Queue] = {}

        logger.info("ConnectionManager initialized")

    async def connect(self, session_id: str, websocket: WebSocket):
        """
        새 WebSocket 연결 등록

        Args:
            session_id: 세션 ID
            websocket: WebSocket 연결 객체
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket

        logger.info(f"[WebSocket] Connected: {session_id}")

        # 재연결 시 큐잉된 메시지 전송
        await self._flush_queued_messages(session_id)

    def disconnect(self, session_id: str):
        """
        WebSocket 연결 해제

        Args:
            session_id: 세션 ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"[WebSocket] Disconnected: {session_id}")

    def _serialize_datetimes(self, obj: Any) -> Any:
        """
        재귀적으로 datetime, Enum 객체를 직렬화 가능한 형식으로 변환

        Args:
            obj: 변환할 객체

        Returns:
            변환된 객체 (datetime은 문자열로, Enum은 값으로 변환됨)
        """
        from enum import Enum

        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {key: self._serialize_datetimes(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._serialize_datetimes(item) for item in obj)
        else:
            return obj

    async def send_message(self, session_id: str, message: dict) -> bool:
        """
        세션에 메시지 전송 (연결 없으면 큐잉)

        Args:
            session_id: 대상 세션 ID
            message: 전송할 메시지 (dict)

        Returns:
            bool: 전송 성공 여부
        """
        websocket = self.active_connections.get(session_id)

        if websocket:
            try:
                # WebSocket 상태 확인 - 닫힌 연결이면 제거하고 큐잉
                if websocket.client_state.name in ["DISCONNECTED", "CLOSED"]:
                    logger.warning(f"WebSocket for {session_id} is closed, removing from active connections")
                    self.disconnect(session_id)
                    await self._queue_message(session_id, message)
                    return False

                # datetime 객체를 ISO 형식 문자열로 자동 변환
                serialized_message = self._serialize_datetimes(message)
                await websocket.send_json(serialized_message)
                logger.debug(f"📤 Sent to {session_id}: {message.get('type', 'unknown')}")
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                # 연결 끊김으로 판단, active_connections에서 제거
                self.disconnect(session_id)
                await self._queue_message(session_id, message)
                return False
        else:
            # 연결 없음 → 큐잉
            await self._queue_message(session_id, message)
            logger.debug(f"📦 Queued for {session_id}: {message.get('type', 'unknown')}")
            return False

    def is_connected(self, session_id: str) -> bool:
        """
        세션 연결 상태 확인

        Args:
            session_id: 세션 ID

        Returns:
            bool: 연결 여부
        """
        return session_id in self.active_connections

    def get_active_count(self) -> int:
        """
        활성 연결 수 반환

        Returns:
            int: 활성 연결 수
        """
        return len(self.active_connections)

    async def _queue_message(self, session_id: str, message: dict):
        """
        메시지 큐에 추가 (내부 메서드)

        Args:
            session_id: 세션 ID
            message: 큐잉할 메시지
        """
        if session_id not in self.message_queues:
            self.message_queues[session_id] = asyncio.Queue()

        await self.message_queues[session_id].put(message)

    async def _flush_queued_messages(self, session_id: str):
        """
        큐잉된 메시지 모두 전송 (재연결 시)

        Args:
            session_id: 세션 ID
        """
        if session_id not in self.message_queues:
            return

        queue = self.message_queues[session_id]
        flushed_count = 0

        while not queue.empty():
            try:
                message = await queue.get()
                await self.send_message(session_id, message)
                flushed_count += 1
            except Exception as e:
                logger.error(f"Failed to flush message for {session_id}: {e}")
                break

        if flushed_count > 0:
            logger.info(f"📨 Flushed {flushed_count} queued messages for {session_id}")

        del self.message_queues[session_id]

    def cleanup_session(self, session_id: str):
        """
        세션 완전 정리 (연결 + 큐)

        Args:
            session_id: 정리할 세션 ID
        """
        self.disconnect(session_id)

        if session_id in self.message_queues:
            del self.message_queues[session_id]
            logger.info(f"🗑️ Cleaned up queues for {session_id}")


# Singleton instance
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """
    ConnectionManager 싱글톤 인스턴스 반환

    Returns:
        ConnectionManager: 싱글톤 인스턴스
    """
    return _connection_manager
