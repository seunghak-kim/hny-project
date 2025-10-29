"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ProgressBar } from "@/components/ui/progress-bar"
import { Send, RefreshCw, Clock } from "lucide-react"
import { useSession } from "@/hooks/use-session"
import { createWSClient, ChatWSClient, type WSMessage } from "@/lib/ws"
import type {
  ExecutionDashboardState,
  TeamExecutionState,
  TeamStep,
  ResponseGenerationState,
  PerformanceMetrics,
  TEAM_DISPLAY_INFO,
  TEAM_STEP_NAMES
} from "@/types/execution"
import {
  TEAM_DISPLAY_INFO as TEAM_INFO,
  TEAM_STEP_NAMES as STEP_NAMES
} from "@/types/execution"

export function ExecutionDashboard() {
  const { sessionId, isLoading: sessionLoading } = useSession()
  const [dashboardState, setDashboardState] = useState<ExecutionDashboardState>({
    active_teams: [],
    status: "idle"
  })
  const [inputValue, setInputValue] = useState("")
  const [wsConnected, setWsConnected] = useState(false)
  const [startTime, setStartTime] = useState<number | null>(null)
  const wsClientRef = useRef<ChatWSClient | null>(null)

  // WebSocket 메시지 핸들러
  const handleWSMessage = useCallback((message: WSMessage) => {
    console.log("[ExecutionDashboard] Received:", message.type)

    switch (message.type) {
      case "connected":
        break

      case "execution_start":
        setStartTime(Date.now())
        setDashboardState((prev) => ({
          ...prev,
          status: "executing",
          active_teams: []
        }))
        break

      case "agent_steps_initialized":
        // 새로운 팀 추가
        if (message.agentName && message.steps) {
          const teamName = message.agentType || message.agentName
          setDashboardState((prev) => {
            const existingTeam = prev.active_teams.find(t => t.team_name === teamName)
            if (existingTeam) return prev

            const newTeam: TeamExecutionState = {
              team_name: teamName,
              status: "running",
              steps: message.steps.map((step: any) => ({
                step_name: step.name,
                status: step.status || "pending",
                progress: step.progress || 0
              })),
              current_step_index: message.currentStepIndex || 0,
              overall_progress: message.overallProgress || 0,
              start_time: new Date().toISOString()
            }

            return {
              ...prev,
              active_teams: [...prev.active_teams, newTeam]
            }
          })
        }
        break

      case "agent_step_progress":
        // 팀의 스텝 진행 상황 업데이트
        setDashboardState((prev) => ({
          ...prev,
          active_teams: prev.active_teams.map(team => {
            if (team.team_name !== message.agentName) return team

            const updatedSteps = team.steps.map((step, idx) => {
              if (idx === message.stepIndex) {
                return {
                  ...step,
                  status: message.status as any,
                  progress: message.progress || step.progress || 0
                }
              }
              return step
            })

            const completedSteps = updatedSteps.filter(s => s.status === "completed").length
            const overallProgress = Math.round((completedSteps / updatedSteps.length) * 100)

            return {
              ...team,
              steps: updatedSteps,
              current_step_index: message.stepIndex,
              overall_progress: overallProgress,
              status: message.status === "failed" ? "failed" : "running"
            }
          })
        }))
        break

      case "todo_updated":
        // ExecutionStep 완료 체크
        if (message.execution_steps) {
          const completedSteps = message.execution_steps.filter((s: any) => s.status === "completed")
          if (completedSteps.length === message.execution_steps.length) {
            // 모든 팀 완료
            setDashboardState((prev) => ({
              ...prev,
              active_teams: prev.active_teams.map(team => ({
                ...team,
                status: "completed",
                end_time: new Date().toISOString()
              }))
            }))
          }
        }
        break

      case "response_generating_start":
        setDashboardState((prev) => ({
          ...prev,
          status: "generating",
          response_generation: {
            phase: message.phase === "aggregation" ? "aggregation" : "response_generation",
            current_phase_progress: 0,
            start_time: new Date().toISOString()
          }
        }))
        break

      case "response_generating_progress":
        setDashboardState((prev) => ({
          ...prev,
          response_generation: prev.response_generation ? {
            ...prev.response_generation,
            phase: message.phase === "aggregation" ? "aggregation" : "response_generation",
            current_phase_progress: 50
          } : undefined
        }))
        break

      case "final_response":
        const endTime = Date.now()
        const totalTime = startTime ? (endTime - startTime) / 1000 : 0

        setDashboardState((prev) => ({
          ...prev,
          status: "completed",
          response_generation: prev.response_generation ? {
            ...prev.response_generation,
            phase: "completed",
            current_phase_progress: 100,
            end_time: new Date().toISOString()
          } : undefined,
          performance_metrics: {
            total_execution_time: totalTime,
            total_llm_calls: 0,  // TODO: 백엔드에서 제공 필요
            total_tokens_used: 0,  // TODO: 백엔드에서 제공 필요
            avg_llm_call_duration: 0,
            team_durations: {}
          }
        }))
        setStartTime(null)
        break
    }
  }, [startTime])

  // WebSocket 초기화
  useEffect(() => {
    if (!sessionId) return

    const wsClient = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
      sessionId,
      onMessage: handleWSMessage,
      onConnected: () => {
        console.log("[ExecutionDashboard] WebSocket connected")
        setWsConnected(true)
      },
      onDisconnected: () => {
        console.log("[ExecutionDashboard] WebSocket disconnected")
        setWsConnected(false)
      },
      onError: (error) => {
        console.error("[ExecutionDashboard] WebSocket error:", error)
      }
    })

    wsClient.connect()
    wsClientRef.current = wsClient

    return () => {
      wsClient.disconnect()
      wsClientRef.current = null
    }
  }, [sessionId, handleWSMessage])

  const handleSendMessage = () => {
    if (!inputValue.trim() || !wsClientRef.current) return

    setDashboardState({
      query: inputValue,
      active_teams: [],
      status: "executing"
    })

    wsClientRef.current.send({
      type: "query",
      query: inputValue,
      enable_checkpointing: true
    })

    setInputValue("")
    setStartTime(Date.now())
  }

  const handleReset = () => {
    setDashboardState({ active_teams: [], status: "idle" })
    setStartTime(null)
  }

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

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">⚙️ Execution Test Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              에이전트 실행 및 성능 테스트 모니터링
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-xs text-muted-foreground">
              {wsConnected ? "연결됨" : "연결 끊김"}
            </span>
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RefreshCw className="w-4 h-4 mr-2" />
              초기화
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-6xl mx-auto space-y-4">
          {/* Query Input */}
          <Card className="p-4">
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="테스트할 질문을 입력하세요..."
                onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                disabled={dashboardState.status !== "idle"}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={dashboardState.status !== "idle" || !inputValue.trim()}
              >
                <Send className="w-4 h-4 mr-2" />
                실행
              </Button>
            </div>
          </Card>

          {/* Current Query */}
          {dashboardState.query && (
            <Card className="p-4 bg-primary/5 border-primary/20">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">실행 중인 질문:</span>
                <span className="text-sm">{dashboardState.query}</span>
              </div>
            </Card>
          )}

          {/* Status Indicator */}
          {dashboardState.status !== "idle" && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">상태:</span>
                <div className="flex items-center gap-2">
                  {dashboardState.status === "executing" && (
                    <>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      <span className="text-sm text-blue-600">팀 실행 중...</span>
                    </>
                  )}
                  {dashboardState.status === "generating" && (
                    <>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                      <span className="text-sm text-purple-600">답변 생성 중...</span>
                    </>
                  )}
                  {dashboardState.status === "completed" && (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-sm text-green-600">완료</span>
                    </>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Team Overview */}
          {dashboardState.active_teams.length > 0 && (
            <Card className="p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">팀 현황</h3>
                  <span className="text-sm text-muted-foreground">
                    {dashboardState.active_teams.filter(t => t.status === "completed").length}/
                    {dashboardState.active_teams.length} 완료
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {dashboardState.active_teams.map((team) => (
                    <TeamExecutionCard key={team.team_name} team={team} />
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* Response Generation */}
          {dashboardState.response_generation && (
            <ResponseGenerationCard data={dashboardState.response_generation} />
          )}

          {/* Performance Metrics */}
          {dashboardState.performance_metrics && dashboardState.status === "completed" && (
            <PerformanceMetricsCard data={dashboardState.performance_metrics} />
          )}

          {/* Empty State */}
          {dashboardState.status === "idle" && !dashboardState.query && (
            <Card className="p-8 text-center">
              <div className="text-6xl mb-4">⚙️</div>
              <h3 className="text-xl font-semibold mb-2">Execution Dashboard</h3>
              <p className="text-muted-foreground mb-4">
                질문을 입력하여 에이전트 실행 과정을 확인하세요
              </p>
              <div className="max-w-md mx-auto text-left space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    팀별 실행 상태 및 서브그래프 진행 상황
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    각 Step의 실시간 진행률 및 상태
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    Response Generation 단계별 진행 상황
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    Performance Metrics (실행 시간, LLM 호출)
                  </span>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Sub Components
// ============================================================================

function TeamExecutionCard({ team }: { team: TeamExecutionState }) {
  const teamInfo = TEAM_INFO[team.team_name] || { label: team.team_name, icon: "🤖", color: "gray" }

  const statusConfig = {
    idle: { color: "text-gray-500", bg: "bg-gray-50 dark:bg-gray-900/20", border: "border-gray-200 dark:border-gray-800" },
    running: { color: "text-blue-600", bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-200 dark:border-blue-800" },
    completed: { color: "text-green-600", bg: "bg-green-50 dark:bg-green-900/20", border: "border-green-200 dark:border-green-800" },
    failed: { color: "text-red-600", bg: "bg-red-50 dark:bg-red-900/20", border: "border-red-200 dark:border-red-800" }
  }

  const config = statusConfig[team.status]

  return (
    <Card className={`p-4 ${config.bg} border ${config.border}`}>
      <div className="space-y-3">
        {/* Team Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{teamInfo.icon}</span>
            <div>
              <div className="font-semibold">{teamInfo.label}</div>
              <div className="text-xs text-muted-foreground">{team.team_name}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Step {team.current_step_index + 1}/{team.steps.length}
            </span>
            {team.status === "running" && (
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            )}
            {team.status === "completed" && (
              <span className={`text-xs font-semibold ${config.color}`}>완료</span>
            )}
          </div>
        </div>

        {/* Overall Progress */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">전체 진행률</span>
            <span className="text-xs font-semibold">{team.overall_progress}%</span>
          </div>
          <ProgressBar value={team.overall_progress} size="sm" showLabel={false} />
        </div>

        {/* Steps */}
        <div className="space-y-1">
          {team.steps.map((step, idx) => (
            <TeamStepRow
              key={idx}
              step={step}
              isActive={idx === team.current_step_index}
            />
          ))}
        </div>

        {/* Duration */}
        {team.start_time && team.end_time && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-border">
            <Clock className="w-3 h-3" />
            <span>
              소요 시간: {team.total_time ? `${team.total_time.toFixed(1)}초` : "계산 중..."}
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}

function TeamStepRow({ step, isActive }: { step: TeamStep; isActive: boolean }) {
  const statusConfig = {
    pending: { icon: "○", color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800" },
    in_progress: { icon: "●", color: "text-blue-600", bg: "bg-blue-100 dark:bg-blue-900/30" },
    completed: { icon: "✓", color: "text-green-600", bg: "bg-green-100 dark:bg-green-900/30" },
    failed: { icon: "✗", color: "text-red-600", bg: "bg-red-100 dark:bg-red-900/30" },
    skipped: { icon: "⊘", color: "text-yellow-600", bg: "bg-yellow-100 dark:bg-yellow-900/30" }
  }

  const config = statusConfig[step.status]

  return (
    <div
      className={`
        flex items-center gap-2 p-2 rounded border transition-all duration-200
        ${isActive ? `${config.bg} border-current scale-105` : "bg-muted/30 border-transparent"}
      `}
    >
      <span className={`text-base ${config.color}`}>{config.icon}</span>
      <span className={`flex-1 text-sm ${isActive ? "font-medium" : ""}`}>
        {step.step_name}
      </span>

      {step.status === "in_progress" && step.progress !== undefined && (
        <div className="w-16">
          <ProgressBar value={step.progress} size="sm" showLabel={false} />
        </div>
      )}

      {step.status === "failed" && step.error && (
        <span className="text-xs text-red-600">실패</span>
      )}
    </div>
  )
}

function ResponseGenerationCard({ data }: { data: ResponseGenerationState }) {
  const phases = [
    { id: "aggregation", label: "데이터 수집", icon: "📥" },
    { id: "response_generation", label: "답변 생성", icon: "✍️" },
    { id: "validation", label: "검증", icon: "✓" }
  ]

  return (
    <Card className="p-4">
      <div className="space-y-3">
        <h3 className="text-lg font-semibold">✍️ Response Generation</h3>

        <div className="grid grid-cols-3 gap-2">
          {phases.map((phase) => {
            const isCompleted = phases.findIndex(p => p.id === data.phase) > phases.findIndex(p => p.id === phase.id)
            const isCurrent = data.phase === phase.id
            const isPending = phases.findIndex(p => p.id === data.phase) < phases.findIndex(p => p.id === phase.id)

            return (
              <div
                key={phase.id}
                className={`
                  p-3 rounded-lg border text-center
                  ${isCompleted ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" :
                    isCurrent ? "bg-primary/10 border-primary" :
                    "bg-muted border-muted-foreground/20 opacity-60"}
                `}
              >
                <div className="text-2xl mb-1">
                  {isCompleted ? "✓" : isCurrent ? phase.icon : "○"}
                </div>
                <div className="text-xs font-medium">{phase.label}</div>
              </div>
            )
          })}
        </div>

        {data.phase !== "completed" && (
          <div className="text-center text-xs text-muted-foreground">
            최적의 답변을 준비하고 있습니다...
          </div>
        )}
      </div>
    </Card>
  )
}

function PerformanceMetricsCard({ data }: { data: PerformanceMetrics }) {
  return (
    <Card className="p-4 bg-secondary/20">
      <div className="space-y-3">
        <h3 className="text-lg font-semibold">📊 Performance Metrics</h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-background rounded-lg border border-border">
            <div className="text-xs text-muted-foreground mb-1">총 실행 시간</div>
            <div className="text-2xl font-bold">{data.total_execution_time.toFixed(1)}s</div>
          </div>

          <div className="p-3 bg-background rounded-lg border border-border">
            <div className="text-xs text-muted-foreground mb-1">LLM 호출</div>
            <div className="text-2xl font-bold">{data.total_llm_calls}</div>
          </div>

          <div className="p-3 bg-background rounded-lg border border-border">
            <div className="text-xs text-muted-foreground mb-1">평균 LLM 시간</div>
            <div className="text-2xl font-bold">
              {data.avg_llm_call_duration > 0 ? `${data.avg_llm_call_duration.toFixed(1)}s` : "N/A"}
            </div>
          </div>

          <div className="p-3 bg-background rounded-lg border border-border">
            <div className="text-xs text-muted-foreground mb-1">토큰 사용</div>
            <div className="text-2xl font-bold">
              {data.total_tokens_used > 0 ? data.total_tokens_used.toLocaleString() : "N/A"}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
