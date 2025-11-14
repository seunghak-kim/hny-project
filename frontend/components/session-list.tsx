"use client"

/**
 * SessionList Component
 *
 * Chat History & State Endpoints
 * - 세션 클릭 시 전환
 * - 세션 삭제 기능
 * - 현재 세션 하이라이트
 */

import { MessageCircle, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { SessionListItem } from "@/types/session"

interface SessionListProps {
  sessions: SessionListItem[]
  currentSessionId: string | null
  onSessionClick: (sessionId: string) => void
  onSessionDelete: (sessionId: string) => Promise<boolean>  // ✅ Promise<boolean> 반환
  isCollapsed?: boolean
}

export function SessionList({
  sessions,
  currentSessionId,
  onSessionClick,
  onSessionDelete,
  isCollapsed = false
}: SessionListProps) {
  /**
   * 상대 시간 표시 (예: "5분 전", "2시간 전")
   */
  const getRelativeTime = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return "방금 전"
    if (diffMins < 60) return `${diffMins}분 전`
    if (diffHours < 24) return `${diffHours}시간 전`
    if (diffDays < 7) return `${diffDays}일 전`
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }

  if (isCollapsed) {
    return (
      <div className="flex flex-col gap-1 px-2">
        {sessions.map((session) => (
          <Button
            key={session.id}
            variant={session.id === currentSessionId ? "secondary" : "ghost"}
            size="icon"
            className="h-10 w-10"
            onClick={() => onSessionClick(session.id)}
            title={session.title}
          >
            <MessageCircle className="h-4 w-4" />
          </Button>
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1 px-2 py-2 max-h-[300px] overflow-y-auto">
      {sessions.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">
          세션이 없습니다.
          <br />
          새 채팅을 시작하세요.
        </div>
      ) : (
        sessions.map((session) => {
          const isActive = session.id === currentSessionId

          return (
            <div
              key={session.id}
              className={`
                group relative px-3 py-2.5 rounded-lg cursor-pointer transition-all
                ${isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground border border-sidebar-border'
                  : 'hover:bg-sidebar-accent/50'
                }
              `}
              onClick={() => onSessionClick(session.id)}
            >
              <div className="flex items-start gap-2">
                {/* 아이콘 */}
                <MessageCircle className={`h-4 w-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />

                {/* 내용 */}
                <div className="flex-1 min-w-0">
                  {/* 제목 */}
                  <p className={`text-sm font-medium truncate ${isActive ? 'text-foreground' : 'text-sidebar-foreground'}`}>
                    {session.title}
                  </p>

                  {/* 마지막 메시지 미리보기 */}
                  {session.last_message && (
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {session.last_message}
                    </p>
                  )}

                  {/* 시간 + 메시지 수 */}
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-muted-foreground">
                      {getRelativeTime(session.updated_at)}
                    </p>
                    {session.message_count > 0 && (
                      <>
                        <span className="text-xs text-muted-foreground">·</span>
                        <p className="text-xs text-muted-foreground">
                          {session.message_count}개 메시지
                        </p>
                      </>
                    )}
                  </div>
                </div>

                {/* 삭제 버튼 (hover 시 표시) */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (window.confirm(`"${session.title}" 세션을 삭제하시겠습니까?`)) {
                      const success = await onSessionDelete(session.id)
                      if (!success) {
                        alert('세션 삭제에 실패했습니다.')
                      }
                    }
                  }}
                >
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
