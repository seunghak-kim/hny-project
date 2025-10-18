"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Send, Bot, User } from "lucide-react"
import type { PageType } from "@/app/page"
import { useSession } from "@/hooks/use-session"
import { ChatWSClient, createWSClient, type WSMessage } from "@/lib/ws"
import type { ExecutionStepState } from "@/lib/types"
import { ExecutionPlanPage } from "@/components/execution-plan-page"
import { ExecutionProgressPage } from "@/components/execution-progress-page"
import { AnswerDisplay } from "@/components/answer-display"
import { GuidancePage } from "@/components/guidance-page"
import type { ProcessState, AgentType } from "@/types/process"
import type { ExecutionPlan, ExecutionStep } from "@/types/execution"
import { STEP_MESSAGES } from "@/types/process"

interface AnswerSection {
  title: string
  content: string | string[]
  icon?: string
  priority?: "high" | "medium" | "low"
  expandable?: boolean
  type?: "text" | "checklist" | "warning"
}

interface AnswerMetadata {
  confidence: number
  sources: string[]
  intent_type: string
}

interface GuidanceData {
  detected_intent: "irrelevant" | "unclear" | "unknown"
  original_query: string
  message: string
}

interface Message {
  id: string
  type: "user" | "bot" | "execution-plan" | "execution-progress" | "guidance"
  content: string
  timestamp: Date
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
  structuredData?: {
    sections: AnswerSection[]
    metadata: AnswerMetadata
  }
  guidanceData?: GuidanceData
}

interface ChatInterfaceProps {
  onSplitView: (agentType: PageType) => void
  currentSessionId?: string | null
}

export function ChatInterface({ onSplitView: _onSplitView, currentSessionId }: ChatInterfaceProps) {
  const { sessionId, isLoading: sessionLoading, error: sessionError } = useSession()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [processState, setProcessState] = useState<ProcessState>({
    step: "idle",
    agentType: null,
    message: ""
  })
  const [todos, setTodos] = useState<ExecutionStepState[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const wsClientRef = useRef<ChatWSClient | null>(null)
  const prevSessionIdRef = useRef<string | null>(null)  // 이전 세션 ID 추적

  const exampleQuestions = [
    "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?",
    "임대차계약이 만료되면 자동으로 갱신되나요?",
    "민간임대주택에서의 수리 의무는 누가 지나요?",
    "관리비의 부과 대상과 납부 의무자는 누구인가요?",
    "부동산 등기에서 사용되는 전문 용어들은 무엇인가요?",
  ]

  // WebSocket 메시지 핸들러
  const handleWSMessage = useCallback((message: WSMessage) => {
    console.log('[ChatInterface] Received WS message:', message.type)

    switch (message.type) {
      case 'connected':
        // 연결 확인 - 아무것도 하지 않음
        break

      // ❌ planning_start는 제거 - 질문 입력 시 즉시 ExecutionPlanPage 표시

      case 'plan_ready':
        // 실행 계획 수신 - 기존 로딩 중인 ExecutionPlanPage 업데이트
        // Backend 전송 형식: { intent, confidence, execution_steps, execution_strategy, estimated_total_time, keywords }
        if (message.intent && message.execution_steps && message.execution_steps.length > 0) {
          // ✅ 정상 케이스: execution_steps가 있는 경우만 업데이트
          setMessages((prev) =>
            prev.map(m =>
              m.type === "execution-plan" && m.executionPlan?.isLoading
                ? {
                    ...m,
                    executionPlan: {
                      intent: message.intent,
                      confidence: message.confidence || 0,
                      execution_steps: message.execution_steps,
                      execution_strategy: message.execution_strategy || "sequential",
                      estimated_total_time: message.estimated_total_time || 5,
                      keywords: message.keywords,
                      isLoading: false  // 로딩 완료
                    }
                  }
                : m
            )
          )
          setTodos(message.execution_steps)

          // ExecutionProgressPage는 execution_start에서 생성됨
        } else {
          // ✅ IRRELEVANT/UNCLEAR: execution_steps가 빈 배열이므로 ExecutionPlanPage 제거
          setMessages((prev) => prev.filter(m => m.type !== "execution-plan"))
        }
        break

      case 'execution_start':
        // 실행 시작 - ExecutionProgressPage 생성
        // Backend 전송 형식: { message, execution_steps, intent, confidence, execution_strategy, estimated_total_time, keywords }
        if (message.execution_steps) {
          const progressMessage: Message = {
            id: `execution-progress-${Date.now()}`,
            type: "execution-progress",
            content: "",
            timestamp: new Date(),
            // ✅ Use complete ExecutionPlan data from Backend (no dependency on Plan message)
            executionPlan: {
              intent: message.intent,
              confidence: message.confidence,
              execution_steps: message.execution_steps,
              execution_strategy: message.execution_strategy,
              estimated_total_time: message.estimated_total_time,
              keywords: message.keywords
            },
            executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
              ...step,
              status: step.status || "pending"
            }))
          }

          // ✅ Remove ExecutionPlanPage and add ExecutionProgressPage
          setMessages((prev) => prev
            .filter(m => m.type !== "execution-plan")
            .concat(progressMessage)
          )

          setProcessState({
            step: "executing",
            agentType: null,
            message: message.message || "작업을 실행하고 있습니다..."
          })
        }
        break

      case 'todo_created':
      case 'todo_updated':
        // TODO 리스트 업데이트
        // Backend 전송 형식: { execution_steps }
        if (message.execution_steps) {
          setTodos(message.execution_steps)

          // ExecutionProgressPage 메시지 찾아서 steps 업데이트
          setMessages((prev) => {
            return prev.map(msg => {
              if (msg.type === "execution-progress") {
                return {
                  ...msg,
                  executionSteps: message.execution_steps
                }
              }
              return msg
            })
          })
        }
        break

      case 'step_start':
        setProcessState({
          step: "executing",
          agentType: message.agent as AgentType,
          message: `${message.task} 실행 중...`
        })
        break


      case 'final_response':
        // 최종 응답 수신
        // ✅ ExecutionPlan과 Progress 모두 제거
        setMessages((prev) => prev.filter(m =>
          m.type !== "execution-progress" && m.type !== "execution-plan"
        ))

        // ✅ Guidance 응답 체크
        if (message.response?.type === "guidance") {
          const guidanceMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: "guidance",
            content: message.response.message,
            timestamp: new Date(),
            guidanceData: {
              detected_intent: message.response.detected_intent || "unknown",
              original_query: message.response.original_query || "",
              message: message.response.message
            }
          }
          setMessages((prev) => [...prev, guidanceMessage])
        } else {
          // 봇 응답 추가 (structured_data 포함)
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: "bot",
            content: message.response?.answer || message.response?.content || message.response?.message || "응답을 받지 못했습니다.",
            structuredData: message.response?.structured_data,
            timestamp: new Date(),
          }
          setMessages((prev) => [...prev, botMessage])
        }
        setTodos([])

        // 프로세스 완료 - idle 상태로 전환하여 입력 활성화
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
        break

      case 'error':
        console.error('[ChatInterface] Error from server:', message.error)
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
        setMessages((prev) => [...prev, {
          id: Date.now().toString(),
          type: "bot",
          content: `오류가 발생했습니다: ${message.error}`,
          timestamp: new Date()
        }])
        break
    }
  }, [])

  // WebSocket 초기화 및 세션 전환 시 재연결
  useEffect(() => {
    // ✅ currentSessionId 우선 사용 (새 채팅 버튼으로 생성된 세션)
    const activeSessionId = currentSessionId || sessionId
    if (!activeSessionId) return

    console.log('[ChatInterface] 🔌 Initializing WebSocket with session:', activeSessionId)

    const wsClient = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
      sessionId: activeSessionId,  // ✅ currentSessionId 또는 sessionId 사용
      onMessage: handleWSMessage,
      onConnected: () => {
        console.log('[ChatInterface] ✅ WebSocket connected to session:', activeSessionId)
        setWsConnected(true)
      },
      onDisconnected: () => {
        console.log('[ChatInterface] WebSocket disconnected')
        setWsConnected(false)
      },
      onError: (error) => {
        console.error('[ChatInterface] WebSocket error:', error)
      }
    })

    wsClient.connect()
    wsClientRef.current = wsClient

    return () => {
      console.log('[ChatInterface] 🔌 Disconnecting WebSocket from session:', activeSessionId)
      wsClient.disconnect()
      wsClientRef.current = null
    }
  }, [currentSessionId, sessionId, handleWSMessage])  // ✅ currentSessionId 추가

  // DB에서 메시지 로드 (WebSocket 연결 후) - 초기 로드용
  useEffect(() => {
    // ✅ currentSessionId 우선 사용
    const activeSessionId = currentSessionId || sessionId
    if (!activeSessionId || !wsConnected) return

    const loadMessagesFromDB = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(
          `${apiUrl}/api/v1/chat/sessions/${activeSessionId}/messages?limit=100`
        )

        if (response.ok) {
          const dbMessages = await response.json()

          // DB에 메시지가 있으면 로드
          if (dbMessages.length > 0) {
            const formattedMessages = dbMessages.map((msg: any) => ({
              id: msg.id.toString(),
              type: msg.role === 'user' ? 'user' : 'bot',
              content: msg.content,
              structuredData: msg.structured_data,  // ✅ 추가
              timestamp: new Date(msg.created_at)
            }))

            // ✅ DB에 메시지가 있으면 환영 메시지 제거하고 DB 메시지로 교체
            setMessages(formattedMessages)
            console.log(`[ChatInterface] ✅ Loaded ${dbMessages.length} messages from DB for session ${activeSessionId}`)
          } else {
            // ✅ DB에 메시지가 없으면 환영 메시지 유지 (초기 상태)
            console.log('[ChatInterface] No messages in DB, keeping welcome message')
          }
        } else {
          console.warn('[ChatInterface] Failed to load messages from DB:', response.status)
        }
      } catch (error) {
        console.error('[ChatInterface] Failed to load messages from DB:', error)
      }
    }

    loadMessagesFromDB()
  }, [currentSessionId, sessionId, wsConnected])  // ✅ currentSessionId 추가

  // 세션 전환 시 메시지 로드 (Chat History 시스템용)
  useEffect(() => {
    // currentSessionId가 없거나 WebSocket이 연결되지 않았으면 실행 안 함
    if (!currentSessionId || !wsConnected) return

    // ✅ 실제로 세션이 변경되었을 때만 실행 (F5 새로고침 시 중복 방지)
    if (prevSessionIdRef.current === currentSessionId) {
      console.log('[ChatInterface] Session unchanged, skipping reload')
      return
    }

    // 이전 세션 ID 업데이트
    prevSessionIdRef.current = currentSessionId

    const loadSessionMessages = async () => {
      try {
        console.log('[ChatInterface] 🔄 Loading session:', currentSessionId)

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(
          `${apiUrl}/api/v1/chat/sessions/${currentSessionId}/messages?limit=100`
        )

        if (response.ok) {
          const dbMessages = await response.json()

          if (dbMessages.length > 0) {
            const formattedMessages = dbMessages.map((msg: any) => ({
              id: msg.id.toString(),
              type: msg.role === 'user' ? 'user' : 'bot',
              content: msg.content,
              structuredData: msg.structured_data,
              timestamp: new Date(msg.created_at)
            }))

            setMessages(formattedMessages)
            console.log(`[ChatInterface] ✅ Loaded ${dbMessages.length} messages for session ${currentSessionId}`)
          } else {
            // 빈 세션 - 환영 메시지만 표시
            setMessages([{
              id: "1",
              type: "bot",
              content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
              timestamp: new Date(),
            }])
            console.log(`[ChatInterface] Session ${currentSessionId} is empty - showing welcome message`)
          }
        }
      } catch (error) {
        console.error('[ChatInterface] Failed to load session messages:', error)
      }
    }

    loadSessionMessages()
  }, [currentSessionId, wsConnected])  // sessionId 의존성 제거 - 충돌 방지

  // 스크롤 자동 이동
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  const handleSendMessage = async (content: string) => {
    // ✅ currentSessionId 우선 사용
    const activeSessionId = currentSessionId || sessionId
    if (!content.trim() || !activeSessionId || !wsClientRef.current) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content,
      timestamp: new Date(),
    }

    // ✅ 즉시 ExecutionPlanPage 추가 (로딩 상태)
    const planMessage: Message = {
      id: `execution-plan-${Date.now()}`,
      type: "execution-plan",
      content: "",
      timestamp: new Date(),
      executionPlan: {
        intent: "분석 중...",
        confidence: 0,
        execution_steps: [],
        execution_strategy: "sequential",
        estimated_total_time: 0,
        keywords: [],
        isLoading: true  // 로딩 상태
      }
    }

    setMessages((prev) => [...prev, userMessage, planMessage])
    setInputValue("")

    // Detect agent type for loading animation
    const agentType = detectAgentType(content) as AgentType | null

    // 프로세스 시작
    setProcessState({
      step: "planning",
      agentType,
      message: STEP_MESSAGES.planning,
      startTime: Date.now()
    })

    // WebSocket으로 쿼리 전송
    wsClientRef.current.send({
      type: "query",
      query: content,
      enable_checkpointing: true
    })

    // 나머지 처리는 handleWSMessage에서 실시간으로 처리됨
  }

  // Helper: Agent 타입 감지 (클라이언트 측 추론)
  const detectAgentType = (content: string): PageType | null => {
    const analysisKeywords = ["계약서", "분석", "등기부등본", "건축물대장"]
    const verificationKeywords = ["허위매물", "전세사기", "위험도", "검증", "신용도"]
    const consultationKeywords = ["추천", "매물", "정책", "지원", "상담", "절차"]

    if (analysisKeywords.some((keyword) => content.includes(keyword))) {
      return "analysis"
    }
    if (verificationKeywords.some((keyword) => content.includes(keyword))) {
      return "verification"
    }
    if (consultationKeywords.some((keyword) => content.includes(keyword))) {
      return "consultation"
    }

    return null
  }

  const handleExampleClick = (question: string) => {
    handleSendMessage(question)
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
    <div className="flex flex-col h-full bg-background">
      <div ref={scrollAreaRef} className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.map((message) => (
            <div key={message.id} className="space-y-2">
              {message.type === "execution-plan" && message.executionPlan && (
                <ExecutionPlanPage plan={message.executionPlan} />
              )}
              {message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
                <ExecutionProgressPage
                  steps={message.executionSteps}
                  plan={message.executionPlan}
                />
              )}
              {message.type === "guidance" && message.guidanceData && (
                <GuidancePage guidance={message.guidanceData} />
              )}
              {(message.type === "user" || message.type === "bot") && (
                <div className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-2 max-w-[80%] ${message.type === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.type === "user" ? "bg-primary" : "bg-secondary"}`}>
                      {message.type === "user" ? <User className="h-4 w-4 text-primary-foreground" /> : <Bot className="h-4 w-4" />}
                    </div>
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

      {/* Example Questions */}
      <div className="border-t border-border p-4">
        <p className="text-sm text-muted-foreground mb-3">예시 질문:</p>
        <div className="flex flex-wrap gap-2 mb-4">
          {exampleQuestions.map((question, index) => (
            <Button
              key={index}
              variant="outline"
              size="sm"
              onClick={() => handleExampleClick(question)}
              className="text-xs"
              disabled={processState.step !== "idle"}
            >
              {question}
            </Button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="메시지를 입력하세요..."
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage(inputValue)}
            disabled={processState.step !== "idle"}
            className="flex-1"
          />
          <Button
            onClick={() => handleSendMessage(inputValue)}
            disabled={processState.step !== "idle" || !inputValue.trim()}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
// DEPRECATED CODE REMOVED - WebSocket으로 완전 전환됨
