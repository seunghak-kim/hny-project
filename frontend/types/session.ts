/**
 * Chat Session Types - Chat History & State Endpoints System
 *
 * 채팅 세션 관리를 위한 TypeScript 타입 정의
 */

import type { Message } from '@/components/chat-interface'

/**
 * 채팅 세션 응답 (백엔드 ChatSessionResponse)
 *
 * GET /sessions, POST /sessions, PATCH /sessions 응답
 */
export interface ChatSessionResponse {
  id: string  // session_id
  title: string
  created_at: string  // ISO 8601 format
  updated_at: string  // ISO 8601 format
  last_message: string | null
  message_count: number
}

/**
 * 세션 목록 아이템 (SessionListItem = ChatSessionResponse의 별칭)
 *
 * 사이드바에 표시할 요약 정보
 */
export type SessionListItem = ChatSessionResponse

/**
 * 채팅 세션 (완전한 데이터)
 *
 * @deprecated Use ChatSessionResponse instead
 */
export type ChatSession = ChatSessionResponse & {
  session_id: string  // id의 별칭
  user_id?: number
  is_active?: boolean
  metadata?: Record<string, any>
}

/**
 * 세션 생성 요청
 */
export interface CreateSessionRequest {
  title?: string
  metadata?: Record<string, any>
}

/**
 * 세션 업데이트 요청
 */
export interface UpdateSessionRequest {
  title?: string
}

/**
 * 세션 삭제 응답 (백엔드)
 */
export interface DeleteSessionResponse {
  message: string
  session_id: string
  deleted_at: string
}
