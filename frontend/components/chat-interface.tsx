"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, History, HelpCircle, ChevronLeft, Plus } from "lucide-react"
import { useSession } from "@/hooks/use-session"
import { LeaseContractPage } from "@/components/lease_contract/lease_contract_page"
import { RightSidebar } from "@/components/right-sidebar"
import { useChat } from "./chat-interface/use-chat"
import { MessageList } from "./chat-interface/message-list"
import { useChatSessions } from "@/hooks/use-chat-sessions"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface ChatInterfaceProps {}

export function ChatInterface({}: ChatInterfaceProps = {}) {
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true)
  const { sessionId, isLoading: sessionLoading, error: sessionError } = useSession()
  const [inputValue, setInputValue] = useState("")

  // Session management for right sidebar - MUST be at top level
  const {
    sessions,
    currentSessionId: managedSessionId,
    createSession,
    switchSession,
    deleteSession,
  } = useChatSessions()

  // Use custom hook for all chat logic
  const activeSessionId = managedSessionId || sessionId
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

  const handleNewChat = async () => {
    const newSessionId = await createSession()
    if (newSessionId) {
      console.log('[ChatInterface] Created new session:', newSessionId)
      // Switch to the new session
      switchSession(newSessionId)
    }
  }

  const exampleQuestions = [
    "전세 보증금 10% 인상 요구하는데 법적으로 문제없어요?",
    "역세권이랑 역전세권 용어 차이 알려줘",
    "방배동 오피스텔 전세 2억 이하로 나온 매물 리스트 보여줘",
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
      <div className="flex h-full bg-background">
        {/* Main Chat Area */}
        <div className={`flex flex-col transition-all duration-300 ease-in-out ${isRightSidebarOpen ? 'flex-1' : 'w-full'}`}>
          {/* Header with help icon and history toggle */}
          <div className="h-20 border-b border-border px-6 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold">홈즈냥 챗봇</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleNewChat}
                className="h-8 w-8"
              >
                <Plus className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <HelpCircle className="h-5 w-5" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-3xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="text-xl">💡 사용법 안내</DialogTitle>
                    <p className="text-sm text-muted-foreground">도와줘 홈즈냥을 활용 가이드</p>
                  </DialogHeader>
                  <div className="space-y-4 text-sm">
                    {/* 용어 설명 및 법률 상담 */}
                    <div className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">📋</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">용어 설명 및 법률 상담</h3>
                          <p className="text-muted-foreground mb-2">부동산 용어와 법률을 쉽게 설명해드립니다</p>
                          <div className="space-y-1 text-blue-600">
                            <p className="font-medium">예시:</p>
                            <p>• "전세금 5% 인상이 가능한가요?"</p>
                            <p>• "임대차보호법이 뭔가요?"</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 매물 정보 및 시세 조회 */}
                    <div className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">🏠</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">매물 정보 및 시세 조회</h3>
                          <p className="text-muted-foreground mb-2">실시간 시장 데이터로 편리하게 저렴합니다</p>
                          <div className="space-y-1 text-blue-600">
                            <p className="font-medium">예시:</p>
                            <p>• "강남구 전세 시세 알려줘"</p>
                            <p>• "서초동 아파트 매매가 얼마야?"</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 인프라 분석 */}
                    <div className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">📊</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">인프라 분석</h3>
                          <p className="text-muted-foreground mb-2">경남/서초/송파구 주변 생활 인프라를 분석합니다</p>
                          <div className="space-y-1 text-blue-600">
                            <p className="font-medium">예시:</p>
                            <p>• "압구정 근처 학군 어때?"</p>
                            <p>• "서초구 가깝 인프라 분석해줘"</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 은행 대출 및 경매 정보 안내 */}
                    <div className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">💰</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">은행 대출 및 경매 정보 안내</h3>
                          <p className="text-muted-foreground mb-2">대출 상담을 경매 지원 정보를 안내합니다</p>
                          <div className="space-y-1 text-blue-600">
                            <p className="font-medium">예시:</p>
                            <p>• "DSR세대대출 산정 비교해줘"</p>
                            <p>• "생애첫 특공금고 지원은?"</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 입대차 계약서 생성 */}
                    <div className="border rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">📝</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">입대차 계약서 생성</h3>
                          <p className="text-muted-foreground mb-2">안전한 계약서 자동으로 지원해드립니다</p>
                          <div className="space-y-1 text-blue-600">
                            <p className="font-medium">예시:</p>
                            <p>• "주내 계약서 만들어줘"</p>
                            <p>• "임대료 계약서 작성해줘"</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 사용 팁 */}
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">💡</span>
                        <div className="flex-1">
                          <h3 className="font-semibold mb-1">사용 팁</h3>
                          <p className="text-muted-foreground">• <strong>구체적인 정보지역, 금액 등</strong>를 함께 입력하시면 더 정확한 답변을 드립니다.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              <Button
                variant={isRightSidebarOpen ? "default" : "ghost"}
                size="icon"
                onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
              >
                {isRightSidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <History className="h-5 w-5" />}
              </Button>
            </div>
          </div>

          {/* 메시지 영역 */}
          <div className="flex-1 overflow-y-auto">
            <MessageList
              messages={messages}
              threeLayerProgress={threeLayerProgress}
              animatedSupervisorProgress={animatedSupervisorProgress}
            />
          </div>

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
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
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

        {/* Right Sidebar - Session List */}
        <RightSidebar
          isOpen={isRightSidebarOpen}
          sessions={sessions}
          currentSessionId={managedSessionId}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
        />
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
