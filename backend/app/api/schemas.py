"""
API Request/Response Schemas
Pydantic models for FastAPI endpoints (HTTP only)
WebSocket messages use JSON directly (see chat_api.py protocol)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# === Session Management ===

class SessionStartRequest(BaseModel):
    """세션 시작 요청 (선택적 필드)"""
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "metadata": {"device": "mobile", "version": "1.0"}
            }
        }


class SessionStartResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    created_at: str
    expires_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-10-08T14:30:00.000Z",
                "expires_at": "2025-10-09T14:30:00.000Z"
            }
        }


# === Error Handling ===

class ErrorResponse(BaseModel):
    """표준 에러 응답"""
    status: str = Field(default="error", description="응답 상태")
    error_code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict] = Field(default=None, description="상세 정보")
    timestamp: str = Field(..., description="에러 발생 시각")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "Query cannot be empty",
                "details": {"field": "query"},
                "timestamp": "2025-10-08T14:30:00.000Z"
            }
        }


# === Session Info ===

class SessionInfo(BaseModel):
    """세션 정보 응답"""
    session_id: str
    created_at: str
    expires_at: str
    last_activity: str
    metadata: Dict[str, Any] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-10-08T14:30:00.000Z",
                "expires_at": "2025-10-09T14:30:00.000Z",
                "last_activity": "2025-10-08T15:45:00.000Z",
                "metadata": {"user_id": "user-123"}
            }
        }


class DeleteSessionResponse(BaseModel):
    """세션 삭제 응답"""
    message: str
    session_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Session deleted",
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000"
            }
        }
