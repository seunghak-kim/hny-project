"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send } from "lucide-react"
import { useSession } from "@/hooks/use-session"
import { LeaseContractPage } from "@/components/lease_contract/lease_contract_page"
import { useChat } from "./chat-interface/use-chat"
import { MessageList } from "./chat-interface/message-list"

interface ChatInterfaceProps {
  currentSessionId?: string | null
}

export function ChatInterface({ currentSessionId }: ChatInterfaceProps) {
  const { sessionId, isLoading: sessionLoading, error: sessionError } = useSession()
  const [inputValue, setInputValue] = useState("")

  // Use custom hook for all chat logic
  const activeSessionId = currentSessionId || sessionId
  const {
    messages,
    wsConnected,
    processState,
    threeLayerProgress,
    animatedSupervisorProgress,
    showLeaseContract,
    leaseContractData,
    sendMessage,
    handleLeaseApprove,
    handleLeaseModify,
    handleLeaseReject,
    closeLeasePopup,
    forceCloseLeasePopup
  } = useChat(activeSessionId)

  const exampleQuestions = [
    "챗봇 사용법 알려줘",
    "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?",
    "전세 보증금 10% 인상 요구하는데 법적으로 문제없어요?",
    "역세권이랑 역전세권 용어 차이 알려줘",
    "성수동 오피스텔 전세 2억 이하로 나온 매물 리스트 보여줘",
  ]

  const handleSendMessage = () => {
    sendMessage(inputValue)
    setInputValue("")
  }

  const handleExampleClick = (question: string) => {
    sendMessage(question)
  }

  // 세션 로딩 중
  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">세션을 초기화하는 중...</p>
        </div>
      </div>
    )
  }

  // 세션 에러
  if (sessionError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-destructive">
          <p className="font-semibold mb-2">세션 생성 실패</p>
          <p className="text-sm">{sessionError}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="flex flex-col h-full bg-background">
        {/* 메시지 영역 */}
        <MessageList
          messages={messages}
          threeLayerProgress={threeLayerProgress}
          animatedSupervisorProgress={animatedSupervisorProgress}
        />

        {/* Example Questions & Input */}
        <div className="flex-shrink-0 border-t border-border px-4 pt-3 pb-2">
          <p className="text-xs text-muted-foreground mb-2">예시 질문:</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {exampleQuestions.map((question, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleExampleClick(question)}
                className="text-xs h-7"
                disabled={processState.step !== "idle"}
              >
                {question}
              </Button>
            ))}
          </div>

          {/* Input */}
          <div className="flex gap-2 mb-0">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="메시지를 입력하세요..."
              onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
              disabled={processState.step !== "idle"}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={processState.step !== "idle" || !inputValue.trim()}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* HITL: 임대차 계약서 페이지 */}
      {showLeaseContract && (
        <LeaseContractPage
          interruptData={leaseContractData?.interrupt_data}
          onApprove={() => {
            handleLeaseApprove()
          }}
          onModify={(modifications: string) => {
            handleLeaseModify(modifications)
          }}
          onReject={() => {
            handleLeaseReject()
          }}
          onClosePopup={() => {
            closeLeasePopup()
          }}
          onClose={() => {
            forceCloseLeasePopup()
          }}
        />
      )}
    </>
  )
}
