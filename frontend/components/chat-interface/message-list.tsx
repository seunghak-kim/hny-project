"use client"

import { useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { User } from "lucide-react"
import Image from "next/image"
import { ProgressContainer } from "@/components/progress-container"
import { AnswerDisplay } from "@/components/answer-display"
import { GuidancePage } from "@/components/guidance-page"
import type { Message } from "./use-chat"
import type { ThreeLayerProgressData } from "@/types/progress"

interface MessageListProps {
  messages: Message[]
  threeLayerProgress: ThreeLayerProgressData | null
  animatedSupervisorProgress: number
}

/**
 * Message list component with auto-scroll
 * Handles rendering of all message types: progress, guidance, user, bot
 */
export function MessageList({ messages, threeLayerProgress, animatedSupervisorProgress }: MessageListProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // 스크롤 자동 이동
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div ref={scrollAreaRef} className="flex-1 overflow-y-auto px-4 py-2">
      <div className="space-y-2 max-w-full mx-auto">
        {messages.map((message) => (
          <div key={message.id} className="space-y-2">
            {/* Progress Message */}
            {message.type === "progress" && (
              <div className="flex justify-start w-full">
                <div className="flex gap-2 w-[80%]">
                  {/* 챗봇 아이콘 */}
                  <div className="flex-shrink-0 w-24 h-24">
                    <Image
                      src="/images/holmesnyangz.png"
                      alt="Holmes Nyangz"
                      width={128}
                      height={128}
                      className="rounded-full object-cover"
                      priority
                    />
                  </div>

                  {/* Progress Container */}
                  <div className="flex-1">
                    {threeLayerProgress ? (
                      <ProgressContainer
                        mode="three-layer"
                        progressData={{
                          ...threeLayerProgress,
                          supervisorProgress: animatedSupervisorProgress
                        }}
                      />
                    ) : message.progressData ? (
                      <ProgressContainer
                        mode="legacy"
                        stage={message.progressData.stage}
                        plan={message.progressData.plan}
                        steps={message.progressData.steps}
                        responsePhase={message.progressData.responsePhase}
                        reusedTeams={message.progressData.reusedTeams}
                      />
                    ) : null}
                  </div>
                </div>
              </div>
            )}

            {/* Guidance Message */}
            {message.type === "guidance" && message.guidanceData && (
              <GuidancePage guidance={message.guidanceData} />
            )}

            {/* User and Bot Messages */}
            {(message.type === "user" || message.type === "bot") && (
              <div className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`flex gap-2 max-w-[80%] ${message.type === "user" ? "flex-row-reverse" : ""}`}>
                  {message.type === "user" ? (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-primary">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  ) : (
                    <div className="flex-shrink-0 w-24 h-24">
                      <Image
                        src="/images/holmesnyangz.png"
                        alt="Holmes Nyangz"
                        width={128}
                        height={128}
                        className="rounded-full object-cover"
                        priority
                      />
                    </div>
                  )}
                  {message.type === "bot" && message.structuredData ? (
                    <AnswerDisplay
                      sections={message.structuredData.sections}
                      metadata={message.structuredData.metadata}
                    />
                  ) : (
                    <Card className={`p-3 ${message.type === "user" ? "bg-primary text-primary-foreground" : ""}`}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </Card>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
