"use client"

import { useState, useCallback } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatInterface } from "@/components/chat-interface"
import { MapInterface } from "@/components/map-interface"
import { AnalysisAgent } from "@/components/agents/analysis-agent"
import { VerificationAgent } from "@/components/agents/verification-agent"
import { ConsultationAgent } from "@/components/agents/consultation-agent"
import { Button } from "@/components/ui/button"
import { Menu, X } from "lucide-react"
import { useChatSessions } from "@/hooks/use-chat-sessions"

export type PageType = "chat" | "map" | "analysis" | "verification" | "consultation"

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageType>("chat")
  const [isSplitView, setIsSplitView] = useState(false)
  const [splitContent, setSplitContent] = useState<PageType | null>(null)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)

  // Session management
  const {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    deleteSession,
  } = useChatSessions()

  const handlePageChange = (page: PageType) => {
    setCurrentPage(page)
    setIsSplitView(false)
    setSplitContent(null)
    setIsMobileSidebarOpen(false)
  }

  const handleSplitView = (agentType: PageType) => {
    setIsSplitView(true)
    setSplitContent(agentType)
  }

  const handleCloseSplitView = () => {
    setIsSplitView(false)
    setSplitContent(null)
  }

  const renderMainContent = () => {
    switch (currentPage) {
      case "chat":
        return <ChatInterface onSplitView={handleSplitView} currentSessionId={currentSessionId} />
      case "map":
        return <MapInterface />
      case "analysis":
        return <AnalysisAgent />
      case "verification":
        return <VerificationAgent />
      case "consultation":
        return <ConsultationAgent />
      default:
        return <ChatInterface onSplitView={handleSplitView} currentSessionId={currentSessionId} />
    }
  }

  const renderSplitContent = () => {
    if (!splitContent) return null

    switch (splitContent) {
      case "analysis":
        return <AnalysisAgent />
      case "verification":
        return <VerificationAgent />
      case "consultation":
        return <ConsultationAgent />
      default:
        return null
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 md:hidden"
        onClick={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
      >
        {isMobileSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </Button>

      {isMobileSidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setIsMobileSidebarOpen(false)} />
      )}

      <div
        className={`
        ${isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0 fixed md:relative z-50 md:z-auto
        transition-transform duration-300 ease-in-out
      `}
      >
        <Sidebar
          currentPage={currentPage}
          onPageChange={handlePageChange}
          sessions={sessions}
          currentSessionId={currentSessionId}
          onCreateSession={createSession}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
        />
      </div>

      <div className="flex-1 flex">
        <div
          className={`
          ${isSplitView ? "w-full lg:w-1/2" : "w-full"} 
          transition-all duration-300
        `}
        >
          {renderMainContent()}
        </div>

        {isSplitView && (
          <div
            className={`
            ${isSplitView ? "fixed lg:relative inset-0 lg:inset-auto lg:w-1/2" : "hidden"}
            bg-background border-l border-border z-30 lg:z-auto
          `}
          >
            <div className="h-full relative">
              <div className="absolute top-4 right-4 z-10 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="lg:hidden bg-transparent"
                  onClick={() => {
                    setCurrentPage(splitContent!)
                    handleCloseSplitView()
                  }}
                >
                  전체화면
                </Button>
                <Button variant="outline" size="icon" onClick={handleCloseSplitView}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {renderSplitContent()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
