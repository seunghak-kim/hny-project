"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { MessageCircle, Home, ChevronLeft, ChevronRight, Plus, Brain, Activity } from "lucide-react"
import type { PageType } from "@/app/page"

interface SidebarProps {
  currentPage: PageType
  onPageChange: (page: PageType) => void
  sessions?: any[]
  currentSessionId?: string | null
  onCreateSession: () => Promise<string | null>
  onSwitchSession?: (sessionId: string) => void
  onDeleteSession?: (sessionId: string) => Promise<boolean>
}

export function Sidebar({
  currentPage,
  onPageChange,
  onCreateSession,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const menuItems = [
    { id: "chat" as PageType, label: "메인 챗봇", icon: MessageCircle },
  ]

  return (
    <div
      className={`${isCollapsed ? "w-16" : "w-64 lg:w-64 md:w-56"} bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300`}
      style={{ height: 'calc(100vh - 64px)' }}
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

        {/* Quick Actions - Dashboards */}
        {!isCollapsed && (
          <div className="mt-8">
            <h3 className="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider mb-3">
              빠른 실행
            </h3>
            <div className="space-y-1">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start gap-2 text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                onClick={() => onPageChange("cognitive_dashboard")}
              >
                <Brain className="h-3 w-3" />
                Cognitive Agent
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start gap-2 text-xs text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                onClick={() => onPageChange("execution_dashboard")}
              >
                <Activity className="h-3 w-3" />
                Execution Agent
              </Button>
            </div>
          </div>
        )}
      </nav>

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
