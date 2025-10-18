import { useState, useEffect } from "react"
import { chatAPI } from "@/lib/api"
import type { SessionStartResponse } from "@/types/chat"

const SESSION_STORAGE_KEY = "holmes_session_id"

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 세션 초기화
  useEffect(() => {
    initSession()
  }, [])

  const initSession = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // 1. sessionStorage에서 기존 세션 확인
      const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

      if (storedSessionId) {
        // ✅ 그냥 바로 사용! (검증 제거 - WebSocket에서 자동 검증됨)
        console.log("✅ Using existing session:", storedSessionId)
        setSessionId(storedSessionId)
        setIsLoading(false)
        return
      }

      // 2. 새 세션 생성 (WebSocket용)
      console.log("🔄 Creating new session...")
      const response = await chatAPI.startSession({
        metadata: {
          device: "web_browser",
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
        },
      })

      console.log("✅ New session created:", response.session_id)
      setSessionId(response.session_id)
      sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
    } catch (err) {
      console.error("❌ Session initialization failed:", err)
      setError(err instanceof Error ? err.message : "Failed to initialize session")
    } finally {
      setIsLoading(false)
    }
  }

  // 세션 재생성
  const resetSession = async () => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    await initSession()
  }

  return {
    sessionId,
    isLoading,
    error,
    resetSession,
  }
}
