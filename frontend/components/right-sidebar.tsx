"use client"

import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, History } from "lucide-react"
import { SessionList } from "@/components/session-list"
import type { SessionListItem } from "@/types/session"
import { useState } from "react"

interface RightSidebarProps {
    isOpen: boolean
    sessions: SessionListItem[]
    currentSessionId: string | null
    onSwitchSession: (sessionId: string) => void
    onDeleteSession: (sessionId: string) => Promise<boolean>
}

export function RightSidebar({
    isOpen,
    sessions,
    currentSessionId,
    onSwitchSession,
    onDeleteSession
}: RightSidebarProps) {
    return (
        <div
            className={`bg-background border-l border-border flex flex-col transition-all duration-300 ease-in-out ${
                isOpen ? "w-64" : "w-0 overflow-hidden"
            }`}
            style={{ height: '100%' }}
        >
            <div className={`flex-1 overflow-hidden ${isOpen ? "opacity-100" : "opacity-0"} transition-opacity duration-300`}>
                <div className="p-4 border-b border-border h-14 flex items-center">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                        <History className="h-4 w-4" />
                        최근 대화
                    </h3>
                </div>

                <div className="overflow-y-auto h-[calc(100%-57px)]">
                    <SessionList
                        sessions={sessions}
                        currentSessionId={currentSessionId}
                        onSessionClick={(sessionId) => {
                            onSwitchSession(sessionId)
                        }}
                        onSessionDelete={onDeleteSession}
                        isCollapsed={false}
                    />
                </div>
            </div>
        </div>
    )
}
