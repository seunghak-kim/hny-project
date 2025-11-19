"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { ChatWSClient, createWSClient, type WSMessage } from "@/lib/ws"
import type { ExecutionStepState } from "@/lib/types"
import type { ProcessState, AgentType } from "@/types/process"
import type { ExecutionPlan, ExecutionStep } from "@/types/execution"
import { STEP_MESSAGES } from "@/types/process"
import type { ThreeLayerProgressData, AgentProgress, SupervisorPhase } from "@/types/progress"
import type { PageType } from "@/app/page"

export interface Message {
  id: string
  type: "user" | "bot" | "progress" | "guidance"
  content: string
  timestamp: Date
  // New: Unified Progress Data (4-stage)
  progressData?: {
    stage: "dispatch" | "analysis" | "executing" | "generating"
    plan?: ExecutionPlan
    steps?: ExecutionStep[]
    responsePhase?: "aggregation" | "response_generation"
    reusedTeams?: string[]
  }
  // Old: Legacy fields (kept for reference, not used)
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
  responseGenerating?: {
    message?: string
    phase?: "aggregation" | "response_generation"
  }
  structuredData?: {
    sections: any[]
    metadata: any
  }
  guidanceData?: {
    detected_intent: "irrelevant" | "unclear" | "unknown" | "usage_guide"
    original_query: string
    message: string
    features?: any[]
    tips?: string[]
  }
}

/**
 * Get default steps for a reused agent
 * Returns completed steps for display purposes
 */
function getDefaultStepsForAgent(agentType: string) {
  const stepTemplates: Record<string, Array<{ id: string; name: string }>> = {
    search: [
      { id: "search_step_1", name: "쿼리 생성" },
      { id: "search_step_2", name: "데이터 검색" },
      { id: "search_step_3", name: "결과 필터링" },
      { id: "search_step_4", name: "결과 정리" }
    ],
    document: [
      { id: "document_step_1", name: "문서 계획" },
      { id: "document_step_2", name: "검색 결과 검증" },
      { id: "document_step_3", name: "정보 입력 (HITL)" },
      { id: "document_step_4", name: "내용 검토 (HITL)" },
      { id: "document_step_5", name: "문서 생성" },
      { id: "document_step_6", name: "최종 확인" }
    ],
    analysis: [
      { id: "analysis_step_1", name: "데이터 수집" },
      { id: "analysis_step_2", name: "데이터 분석" },
      { id: "analysis_step_3", name: "패턴 인식" },
      { id: "analysis_step_4", name: "인사이트 생성" },
      { id: "analysis_step_5", name: "리포트 작성" }
    ]
  }

  const template = stepTemplates[agentType] || stepTemplates["search"]

  return template.map((step) => ({
    id: step.id,
    name: step.name,
    status: "completed" as const,
    progress: 100
  }))
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

export interface UseChatReturn {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  wsConnected: boolean
  processState: ProcessState
  setProcessState: React.Dispatch<React.SetStateAction<ProcessState>>
  todos: ExecutionStepState[]
  setTodos: React.Dispatch<React.SetStateAction<ExecutionStepState[]>>
  threeLayerProgress: ThreeLayerProgressData | null
  animatedSupervisorProgress: number
  showLeaseContract: boolean
  leaseContractData: any
  sendMessage: (content: string) => void
  handleLeaseApprove: () => void
  handleLeaseModify: (modifications: string) => void
  handleLeaseReject: () => void
  closeLeasePopup: () => void
  forceCloseLeasePopup: () => void
}

/**
 * Custom hook for chat WebSocket connection, session management, and message handling
 */
export function useChat(sessionId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
      timestamp: new Date(),
    },
  ])
  const [processState, setProcessState] = useState<ProcessState>({
    step: "idle",
    agentType: null,
    message: ""
  })
  const [todos, setTodos] = useState<ExecutionStepState[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const wsClientRef = useRef<ChatWSClient | null>(null)
  const prevSessionIdRef = useRef<string | null>(null)

  // HITL: 임대차 계약서 페이지 상태
  const [showLeaseContract, setShowLeaseContract] = useState(false)
  const [leaseContractData, setLeaseContractData] = useState<any>(null)

  // 3-Layer Progress System State
  const [threeLayerProgress, setThreeLayerProgress] = useState<ThreeLayerProgressData | null>(null)

  // Animated supervisor progress for smooth visual flow
  const [animatedSupervisorProgress, setAnimatedSupervisorProgress] = useState(0)

  // WebSocket 메시지 핸들러
  const handleWSMessage = useCallback((message: WSMessage) => {
    console.log('[useChat] Received WS message:', message.type)

    switch (message.type) {
      case 'connected':
        // 연결 확인 - 아무것도 하지 않음
        break

      case 'analysis_start':
        // Stage 1 → 2: Dispatch → Analysis (0.5초 딜레이 추가)
        setTimeout(() => {
          setMessages((prev) =>
            prev.map(m =>
              m.type === "progress" && m.progressData?.stage === "dispatch"
                ? {
                    ...m,
                    progressData: {
                      ...m.progressData,
                      stage: "analysis" as const
                    }
                  }
                : m
            )
          )
        }, 500)  // 0.5초 딜레이
        break

      case 'plan_ready':
        // Stage 2: Analysis - plan 데이터 추가
        if (message.execution_steps?.length > 0) {
          setMessages((prev) =>
            prev.map(m =>
              m.type === "progress" && m.progressData?.stage === "analysis"
                ? {
                    ...m,
                    progressData: {
                      ...m.progressData,
                      plan: {
                        intent: message.intent,
                        confidence: message.confidence || 0,
                        execution_steps: message.execution_steps,
                        execution_strategy: message.execution_strategy || "sequential",
                        estimated_total_time: message.estimated_total_time || 5,
                        keywords: message.keywords,
                        isLoading: false
                      }
                    }
                  }
                : m
            )
          )
          setTodos(message.execution_steps)
        } else {
          // IRRELEVANT/UNCLEAR: progress 제거
          setMessages((prev) => prev.filter(m => m.type !== "progress"))
        }
        break

      case 'execution_start':
        // Stage 2 → 3: Analysis → Executing
        if (message.execution_steps) {
          setMessages((prev) =>
            prev.map(m =>
              m.type === "progress"
                ? {
                    ...m,
                    progressData: {
                      stage: "executing" as const,
                      plan: {
                        intent: message.intent,
                        confidence: message.confidence,
                        execution_steps: message.execution_steps,
                        execution_strategy: message.execution_strategy,
                        estimated_total_time: message.estimated_total_time,
                        keywords: message.keywords,
                        isLoading: false
                      },
                      steps: message.execution_steps.map((step: ExecutionStep) => ({
                        ...step,
                        status: step.status || "pending"
                      }))
                    }
                  }
                : m
            )
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
        // Stage 3: Executing - steps 업데이트
        if (message.execution_steps) {
          setTodos(message.execution_steps)

          setMessages((prev) =>
            prev.map(msg =>
              msg.type === "progress" && msg.progressData?.stage === "executing"
                ? {
                    ...msg,
                    progressData: {
                      ...msg.progressData,
                      steps: message.execution_steps
                    }
                  }
                : msg
            )
          )
        }
        break

      case 'step_start':
        setProcessState({
          step: "executing",
          agentType: message.agent as AgentType,
          message: `${message.task} 실행 중...`
        })
        break

      case 'response_generating_start':
        // Stage 3 → 4: Executing → Generating
        setMessages((prev) =>
          prev.map(m =>
            m.type === "progress"
              ? {
                  ...m,
                  progressData: {
                    ...m.progressData,
                    stage: "generating" as const,
                    responsePhase: message.phase || "aggregation"
                  }
                }
              : m
          )
        )

        setProcessState({
          step: "generating_response",
          agentType: null,
          message: message.message || "답변을 생성하고 있습니다..."
        })
        break

      case 'response_generating_progress':
        // Stage 4: Generating - responsePhase 업데이트
        setMessages((prev) =>
          prev.map(m =>
            m.type === "progress" && m.progressData?.stage === "generating"
              ? {
                  ...m,
                  progressData: {
                    ...m.progressData,
                    responsePhase: message.phase || "response_generation"
                  }
                }
              : m
          )
        )
        break

      case 'final_response':
        // 최종 응답 수신 - Progress 제거
        setMessages((prev) => prev.filter(m => m.type !== "progress"))

        // Usage Guide 및 Guidance 응답 체크
        if (message.response?.type === "usage_guide" || message.response?.type === "guidance") {
          const guidanceMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: "guidance",
            content: message.response.message,
            timestamp: new Date(),
            guidanceData: {
              detected_intent: message.response.detected_intent || message.response.type || "unknown",
              original_query: message.response.original_query || "",
              message: message.response.message,
              features: message.response.features,
              tips: message.response.tips
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

        // Reset 3-Layer Progress System
        setThreeLayerProgress(null)

        // 프로세스 완료 - idle 상태로 전환하여 입력 활성화
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
        break

      case 'data_reuse_notification':
        // 재사용된 팀 정보를 Legacy 및 3-Layer Progress에 모두 추가
        if (message.reused_teams && Array.isArray(message.reused_teams)) {
          console.log('[useChat] data_reuse_notification received:', message.reused_teams)

          // Legacy progress 업데이트
          setMessages((prev) =>
            prev.map(m =>
              m.type === "progress" && m.progressData
                ? {
                    ...m,
                    progressData: {
                      ...m.progressData,
                      reusedTeams: message.reused_teams
                    }
                  }
                : m
            )
          )

          // 3-Layer Progress에 재사용 Agent 추가
          setThreeLayerProgress((prev) => {
            if (!prev) return prev

            const reusedAgents: AgentProgress[] = message.reused_teams.map((teamName: string) => ({
              agentName: teamName,
              agentType: teamName,
              steps: getDefaultStepsForAgent(teamName),
              currentStepIndex: 0,
              totalSteps: getDefaultStepsForAgent(teamName).length,
              overallProgress: 100,
              status: "completed" as const,
              isReused: true
            }))

            return {
              ...prev,
              activeAgents: [...prev.activeAgents, ...reusedAgents]
            }
          })
        }
        break

      case 'workflow_interrupted':
        // HITL: 워크플로우 중단 - 임대차 계약서 페이지 표시
        console.log('[useChat] Workflow interrupted:', message)
        setLeaseContractData({
          interrupt_data: message.interrupt_data,
          interrupted_by: message.interrupted_by,
          interrupt_type: message.interrupt_type,
          message: message.message
        })
        setShowLeaseContract(true)

        // Progress 상태는 유지 (사용자가 페이지를 닫을 때까지)
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
        break

      case 'supervisor_phase_change':
        // Layer 1: Supervisor Phase Update
        setThreeLayerProgress((prev) => ({
          supervisorPhase: message.supervisorPhase as SupervisorPhase,
          supervisorProgress: message.supervisorProgress || 0,
          activeAgents: prev?.activeAgents || []
        }))
        break

      case 'agent_steps_initialized':
        // Layer 2: Agent Steps Initialized
        if (message.agentName && message.steps) {
          const newAgent: AgentProgress = {
            agentName: message.agentName,
            agentType: message.agentType || message.agentName,
            steps: message.steps,
            currentStepIndex: message.currentStepIndex || 0,
            totalSteps: message.totalSteps || message.steps.length,
            overallProgress: message.overallProgress || 0,
            status: message.status || "idle"
          }

          setThreeLayerProgress((prev) => ({
            supervisorPhase: prev?.supervisorPhase || "dispatching",
            supervisorProgress: prev?.supervisorProgress || 0,
            activeAgents: [...(prev?.activeAgents || []), newAgent]
          }))
        }
        break

      case 'agent_step_progress':
        // Layer 2: Real-time Step Progress Update
        setThreeLayerProgress((prev) => {
          if (!prev) return prev  // No active progress

          return {
            ...prev,
            activeAgents: prev.activeAgents.map(agent => {
              // Find matching agent
              if (agent.agentName !== message.agentName) {
                return agent  // Not this agent, skip
              }

              // Update matching agent's steps
              const updatedSteps = agent.steps.map((step, idx) => {
                if (idx === message.stepIndex) {
                  return {
                    ...step,
                    status: message.status as "pending" | "in_progress" | "completed" | "failed",
                    progress: message.progress || step.progress || 0
                  }
                }
                return step
              })

              // Calculate overall progress (average of all steps)
              const completedSteps = updatedSteps.filter(s => s.status === "completed").length
              const inProgressSteps = updatedSteps.filter(s => s.status === "in_progress").length
              const overallProgress = Math.round(
                ((completedSteps * 100) + (inProgressSteps * 50)) / updatedSteps.length
              )

              return {
                ...agent,
                steps: updatedSteps,
                currentStepIndex: message.stepIndex,
                overallProgress: overallProgress,
                status: message.status === "failed" ? ("failed" as const) : ("running" as const)
              }
            })
          }
        })
        break

      case 'error':
        console.error('[useChat] Error from server:', message.error)
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
    if (!sessionId) return

    console.log('[useChat] 🔌 Initializing WebSocket with session:', sessionId)

    const wsClient = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
      sessionId: sessionId,
      onMessage: handleWSMessage,
      onConnected: () => {
        console.log('[useChat] ✅ WebSocket connected to session:', sessionId)
        setWsConnected(true)
      },
      onDisconnected: () => {
        console.log('[useChat] WebSocket disconnected')
        setWsConnected(false)
      },
      onError: (error) => {
        console.error('[useChat] WebSocket error:', error)
      }
    })

    wsClient.connect()
    wsClientRef.current = wsClient

    return () => {
      console.log('[useChat] 🔌 Disconnecting WebSocket from session:', sessionId)
      wsClient.disconnect()
      wsClientRef.current = null
    }
  }, [sessionId, handleWSMessage])

  // Smooth supervisor progress animation
  useEffect(() => {
    if (!threeLayerProgress) {
      setAnimatedSupervisorProgress(0)
      return
    }

    const targetProgress = threeLayerProgress.supervisorProgress
    const currentProgress = animatedSupervisorProgress

    // If already at target, do nothing
    if (currentProgress === targetProgress) return

    // If target is 100 (completed), jump immediately
    if (targetProgress === 100) {
      setAnimatedSupervisorProgress(100)
      return
    }

    // Smooth animation from current to target
    const duration = 200 // ms per increment
    const increment = targetProgress > currentProgress ? 1 : -1

    const interval = setInterval(() => {
      setAnimatedSupervisorProgress((prev) => {
        if (increment > 0 && prev >= targetProgress) {
          clearInterval(interval)
          return targetProgress
        }
        if (increment < 0 && prev <= targetProgress) {
          clearInterval(interval)
          return targetProgress
        }
        return prev + increment
      })
    }, duration)

    return () => clearInterval(interval)
  }, [threeLayerProgress?.supervisorProgress, animatedSupervisorProgress])

  // DB에서 메시지 로드 (WebSocket 연결 후) - 초기 로드용
  useEffect(() => {
    if (!sessionId || !wsConnected) return

    const loadMessagesFromDB = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(
          `${apiUrl}/api/v1/chat/sessions/${sessionId}/messages?limit=100`
        )

        if (response.ok) {
          const dbMessages = await response.json()

          // DB에 메시지가 있으면 로드
          if (dbMessages.length > 0) {
            const formattedMessages = dbMessages.map((msg: any) => ({
              id: msg.id.toString(),
              type: msg.role === 'user' ? 'user' : 'bot',
              content: msg.content,
              structuredData: msg.structured_data,
              timestamp: new Date(msg.created_at)
            }))

            // DB에 메시지가 있으면 환영 메시지 제거하고 DB 메시지로 교체
            setMessages(formattedMessages)
            console.log(`[useChat] ✅ Loaded ${dbMessages.length} messages from DB for session ${sessionId}`)
          } else {
            // DB에 메시지가 없으면 환영 메시지 유지 (초기 상태)
            console.log('[useChat] No messages in DB, keeping welcome message')
          }
        } else {
          console.warn('[useChat] Failed to load messages from DB:', response.status)
        }
      } catch (error) {
        console.error('[useChat] Failed to load messages from DB:', error)
      }
    }

    loadMessagesFromDB()
  }, [sessionId, wsConnected])

  // 세션 전환 시 메시지 로드 (Chat History 시스템용)
  useEffect(() => {
    // sessionId가 없거나 WebSocket이 연결되지 않았으면 실행 안 함
    if (!sessionId || !wsConnected) return

    // 실제로 세션이 변경되었을 때만 실행 (F5 새로고침 시 중복 방지)
    if (prevSessionIdRef.current === sessionId) {
      console.log('[useChat] Session unchanged, skipping reload')
      return
    }

    // 이전 세션 ID 업데이트
    prevSessionIdRef.current = sessionId

    const loadSessionMessages = async () => {
      try {
        console.log('[useChat] 🔄 Loading session:', sessionId)

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(
          `${apiUrl}/api/v1/chat/sessions/${sessionId}/messages?limit=100`
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
            console.log(`[useChat] ✅ Loaded ${dbMessages.length} messages for session ${sessionId}`)
          } else {
            // 빈 세션 - 환영 메시지만 표시
            setMessages([{
              id: "1",
              type: "bot",
              content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
              timestamp: new Date(),
            }])
            console.log(`[useChat] Session ${sessionId} is empty - showing welcome message`)
          }
        }
      } catch (error) {
        console.error('[useChat] Failed to load session messages:', error)
      }
    }

    loadSessionMessages()
  }, [sessionId, wsConnected])

  // 메시지 전송 함수
  const sendMessage = useCallback((content: string) => {
    if (!content.trim() || !sessionId || !wsClientRef.current) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content,
      timestamp: new Date(),
    }

    // Stage 1: Dispatch 즉시 표시
    const progressMessage: Message = {
      id: `progress-${Date.now()}`,
      type: "progress",
      content: "",
      timestamp: new Date(),
      progressData: {
        stage: "dispatch",
        plan: {
          intent: "분석 중...",
          confidence: 0,
          execution_steps: [],
          execution_strategy: "sequential",
          estimated_total_time: 0,
          keywords: [],
          isLoading: true
        }
      }
    }

    setMessages((prev) => [...prev, userMessage, progressMessage])

    // Initialize 3-Layer Progress System
    setThreeLayerProgress({
      supervisorPhase: "dispatching",
      supervisorProgress: 0,
      activeAgents: []
    })

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
  }, [sessionId])

  // HITL 핸들러
  const handleLeaseApprove = useCallback(() => {
    if (wsClientRef.current) {
      console.log('[useChat] Sending approve response')
      wsClientRef.current.send({
        type: "interrupt_response",
        action: "approve",
        feedback: null
      })
    }
  }, [])

  const handleLeaseModify = useCallback((modifications: string) => {
    if (wsClientRef.current) {
      console.log('[useChat] Sending modify response:', modifications)
      wsClientRef.current.send({
        type: "interrupt_response",
        action: "modify",
        feedback: modifications,
        modifications: modifications
      })
    }
  }, [])

  const handleLeaseReject = useCallback(() => {
    if (wsClientRef.current) {
      console.log('[useChat] Sending reject response')
      wsClientRef.current.send({
        type: "interrupt_response",
        action: "reject",
        feedback: null
      })
    }
  }, [])

  const closeLeasePopup = useCallback(() => {
    // 승인/수정/거부 후: 팝업만 닫기 (Progress 유지)
    console.log('[useChat] Closing popup only (keeping progress visible)')
    setShowLeaseContract(false)
    setLeaseContractData(null)
    // Progress는 삭제하지 않음! final_response 수신 시 자동 제거됨
  }, [])

  const forceCloseLeasePopup = useCallback(() => {
    // X 버튼으로 강제 종료: 팝업 닫기 + Progress 제거
    console.log('[useChat] Force closing popup (removing progress)')
    setShowLeaseContract(false)
    setLeaseContractData(null)
    // X 버튼으로 닫을 때만 Progress 제거
    setMessages((prev) => prev.filter(m => m.type !== "progress"))
  }, [])

  return {
    messages,
    setMessages,
    wsConnected,
    processState,
    setProcessState,
    todos,
    setTodos,
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
  }
}
