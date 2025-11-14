import type {
  SessionStartRequest,
  SessionStartResponse,
  ChatRequest,
  ChatResponse,
  SessionInfo,
  DeleteSessionResponse,
  SessionStats,
} from "@/types/chat"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_PREFIX = "/api/v1/chat"

class ChatAPIService {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_PREFIX}`
  }

  /**
   * 새 세션 시작
   */
  async startSession(request: SessionStartRequest = {}): Promise<SessionStartResponse> {
    const response = await fetch(`${this.baseUrl}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 채팅 메시지 전송
   */
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `Failed to send message: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 세션 정보 조회
   */
  async getSessionInfo(sessionId: string): Promise<SessionInfo> {
    const response = await fetch(`${this.baseUrl}/${sessionId}`)

    if (!response.ok) {
      throw new Error(`Failed to get session info: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 세션 삭제
   */
  async deleteSession(sessionId: string): Promise<DeleteSessionResponse> {
    const response = await fetch(`${this.baseUrl}/${sessionId}`, {
      method: "DELETE",
    })

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 세션 통계 조회
   */
  async getSessionStats(): Promise<SessionStats> {
    const response = await fetch(`${this.baseUrl}/stats/sessions`)

    if (!response.ok) {
      throw new Error(`Failed to get session stats: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 만료된 세션 정리
   */
  async cleanupExpiredSessions(): Promise<{ message: string; cleaned_count: number }> {
    const response = await fetch(`${this.baseUrl}/cleanup/sessions`, {
      method: "POST",
    })

    if (!response.ok) {
      throw new Error(`Failed to cleanup sessions: ${response.statusText}`)
    }

    return response.json()
  }
}

export const chatAPI = new ChatAPIService()
