"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { MessageCircle, Map, FileText, Shield, Users, Home, ChevronLeft, ChevronRight, Plus } from "lucide-react"
import { SessionList } from "@/components/session-list"
import type { PageType } from "@/app/page"
import type { SessionListItem } from "@/hooks/use-chat-sessions"

interface SidebarProps {
  currentPage: PageType
  onPageChange: (page: PageType) => void
  sessions: SessionListItem[]
  currentSessionId: string | null
  onCreateSession: () => Promise<string | null>
  onSwitchSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => Promise<boolean>
}

export function Sidebar({
  currentPage,
  onPageChange,
  sessions,
  currentSessionId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const menuItems = [
    { id: "chat" as PageType, label: "메인 챗봇", icon: MessageCircle },
    { id: "map" as PageType, label: "지도 검색", icon: Map },
    { id: "analysis" as PageType, label: "분석 에이전트", icon: FileText },
    { id: "verification" as PageType, label: "검증 에이전트", icon: Shield },
    { id: "consultation" as PageType, label: "상담 에이전트", icon: Users },
  ]

  return (
    <div
      className={`${isCollapsed ? "w-16" : "w-64 lg:w-64 md:w-56"} bg-sidebar border-r border-sidebar-border flex flex-col h-screen transition-all duration-300`}
    >
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between">
          <div className={`flex items-center gap-2 ${isCollapsed ? "justify-center" : ""}`}>
            <Home className="h-6 w-6 text-sidebar-primary" />
            {!isCollapsed && (
              <div>
                <h1 className="font-bold text-lg text-sidebar-foreground">도와줘 홈즈냥즈</h1>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="text-sidebar-foreground hover:bg-sidebar-accent"
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
        {!isCollapsed && <p className="text-sm text-sidebar-foreground/70 mt-1">AI 부동산 가디언</p>}
      </div>

      {/* 새 채팅 버튼 */}
      {!isCollapsed && (
        <div className="p-4 border-b border-sidebar-border">
          <Button
            onClick={async () => {
              const newSessionId = await onCreateSession()
              if (newSessionId) {
                console.log('[Sidebar] Created new session:', newSessionId)
                onPageChange("chat")
              }
            }}
            className="w-full gap-2"
            variant="default"
          >
            <Plus className="h-4 w-4" />
            새 채팅
          </Button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = currentPage === item.id

            return (
              <Button
                key={item.id}
                variant={isActive ? "default" : "ghost"}
                className={`w-full ${isCollapsed ? "justify-center px-2" : "justify-start gap-3"} ${
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
                onClick={() => onPageChange(item.id)}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon className="h-4 w-4" />
                {!isCollapsed && <span className="text-sm">{item.label}</span>}
              </Button>
            )
          })}
        </div>

        {/* Agent Quick Actions */}
        {!isCollapsed && (
          <div className="mt-8">
            <h3 className="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider mb-3">
              빠른 실행
            </h3>
            <div className="space-y-1">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground"
                onClick={() => onPageChange("analysis")}
              >
                계약서 분석
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground"
                onClick={() => onPageChange("verification")}
              >
                허위매물 검증
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground"
                onClick={() => onPageChange("consultation")}
              >
                매물 추천
              </Button>
            </div>
          </div>
        )}
      </nav>

      {/* Session List */}
      {!isCollapsed && (
        <div className="border-t border-sidebar-border py-4">
          <h3 className="px-4 mb-3 text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider">
            최근 대화
          </h3>
          <SessionList
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSessionClick={(sessionId) => {
              onSwitchSession(sessionId)
              onPageChange("chat")
            }}
            onSessionDelete={onDeleteSession}
            isCollapsed={isCollapsed}
          />
        </div>
      )}

      {/* Footer */}
      {!isCollapsed && (
        <div className="p-4 border-t border-sidebar-border">
          <p className="text-xs text-sidebar-foreground/50 text-center">
            안전한 부동산 거래를 위한
            <br />
            AI 파트너
          </p>
        </div>
      )}
    </div>
  )
}
