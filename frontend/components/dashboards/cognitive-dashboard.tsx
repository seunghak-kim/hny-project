"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ProgressBar } from "@/components/ui/progress-bar"
import { Send, RefreshCw } from "lucide-react"
import { useSession } from "@/hooks/use-session"
import { createWSClient, ChatWSClient, type WSMessage } from "@/lib/ws"
import type {
  CognitiveState,
  IntentAnalysisData,
  AgentSelectionData,
  ExecutionPlanData,
  MemoryLoadData,
  DataReuseInfo,
  INTENT_TYPE_DISPLAY,
  AGENT_NAME_DISPLAY,
  SELECTION_LAYER_DISPLAY
} from "@/types/cognitive"
import {
  INTENT_TYPE_DISPLAY as INTENT_DISPLAY,
  AGENT_NAME_DISPLAY as AGENT_DISPLAY,
  SELECTION_LAYER_DISPLAY as LAYER_DISPLAY
} from "@/types/cognitive"

export function CognitiveDashboard() {
  const { sessionId, isLoading: sessionLoading } = useSession()
  const [cognitiveState, setCognitiveState] = useState<CognitiveState>({
    phase: "idle"
  })
  const [inputValue, setInputValue] = useState("")
  const [wsConnected, setWsConnected] = useState(false)
  const wsClientRef = useRef<ChatWSClient | null>(null)

  // WebSocket 메시지 핸들러
  const handleWSMessage = useCallback((message: WSMessage) => {
    console.log("[CognitiveDashboard] Received:", message.type)

    switch (message.type) {
      case "connected":
        break

      case "analysis_start":
        setCognitiveState((prev) => ({
          ...prev,
          phase: "analyzing"
        }))
        break

      case "plan_ready":
        // Intent Analysis + Execution Plan
        if (message.execution_steps && message.execution_steps.length > 0) {
          setCognitiveState((prev) => ({
            ...prev,
            intent_analysis: {
              intent_type: message.intent,
              confidence: message.confidence || 0,
              keywords: message.keywords || [],
              reasoning: "",
              timestamp: new Date().toISOString()
            },
            execution_plan: {
              execution_steps: message.execution_steps,
              execution_strategy: message.execution_strategy || "sequential",
              estimated_total_time: message.estimated_total_time || 0
            },
            phase: "planning"
          }))
        } else {
          // IRRELEVANT/UNCLEAR
          setCognitiveState((prev) => ({
            ...prev,
            intent_analysis: {
              intent_type: message.intent,
              confidence: message.confidence || 0,
              keywords: message.keywords || [],
              reasoning: "조기 종료 (IRRELEVANT/UNCLEAR)",
              timestamp: new Date().toISOString()
            },
            phase: "completed"
          }))
        }
        break

      case "data_reuse_notification":
        if (message.reused_teams) {
          setCognitiveState((prev) => ({
            ...prev,
            data_reuse: {
              reused: true,
              reused_teams: message.reused_teams,
              reused_from_message: message.reused_from_message,
              timestamp: new Date().toISOString()
            }
          }))
        }
        break

      case "execution_start":
        setCognitiveState((prev) => ({
          ...prev,
          phase: "completed"
        }))
        break
    }
  }, [])

  // WebSocket 초기화
  useEffect(() => {
    if (!sessionId) return

    const wsClient = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
      sessionId,
      onMessage: handleWSMessage,
      onConnected: () => {
        console.log("[CognitiveDashboard] WebSocket connected")
        setWsConnected(true)
      },
      onDisconnected: () => {
        console.log("[CognitiveDashboard] WebSocket disconnected")
        setWsConnected(false)
      },
      onError: (error) => {
        console.error("[CognitiveDashboard] WebSocket error:", error)
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

    setCognitiveState({
      query: inputValue,
      phase: "analyzing"
    })

    wsClientRef.current.send({
      type: "query",
      query: inputValue,
      enable_checkpointing: true
    })

    setInputValue("")
  }

  const handleReset = () => {
    setCognitiveState({ phase: "idle" })
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
            <h1 className="text-2xl font-bold">🧠 Cognitive Performance Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              의도 분석 및 실행 계획 수립 과정 모니터링
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
                disabled={cognitiveState.phase !== "idle"}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={cognitiveState.phase !== "idle" || !inputValue.trim()}
              >
                <Send className="w-4 h-4 mr-2" />
                분석
              </Button>
            </div>
          </Card>

          {/* Current Query */}
          {cognitiveState.query && (
            <Card className="p-4 bg-primary/5 border-primary/20">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">분석 중인 질문:</span>
                <span className="text-sm">{cognitiveState.query}</span>
              </div>
            </Card>
          )}

          {/* Phase Indicator */}
          {cognitiveState.phase !== "idle" && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">진행 단계:</span>
                <div className="flex items-center gap-2">
                  {cognitiveState.phase === "analyzing" && (
                    <>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      <span className="text-sm text-blue-600">의도 분석 중...</span>
                    </>
                  )}
                  {cognitiveState.phase === "planning" && (
                    <>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                      <span className="text-sm text-purple-600">실행 계획 수립 중...</span>
                    </>
                  )}
                  {cognitiveState.phase === "completed" && (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-sm text-green-600">분석 완료</span>
                    </>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Intent Analysis Card */}
          {cognitiveState.intent_analysis && (
            <IntentAnalysisCard data={cognitiveState.intent_analysis} />
          )}

          {/* Agent Selection Card (추후 구현 - LLM 추적 정보 필요) */}
          {/* {cognitiveState.agent_selection && (
            <AgentSelectionCard data={cognitiveState.agent_selection} />
          )} */}

          {/* Execution Plan Card */}
          {cognitiveState.execution_plan && (
            <ExecutionPlanCard data={cognitiveState.execution_plan} />
          )}

          {/* Data Reuse Card */}
          {cognitiveState.data_reuse && cognitiveState.data_reuse.reused && (
            <DataReuseCard data={cognitiveState.data_reuse} />
          )}

          {/* Memory Status Card (추후 구현 - 백엔드 메시지 필요) */}
          {/* {cognitiveState.memory_load && (
            <MemoryStatusCard data={cognitiveState.memory_load} />
          )} */}

          {/* Empty State */}
          {cognitiveState.phase === "idle" && !cognitiveState.query && (
            <Card className="p-8 text-center">
              <div className="text-6xl mb-4">🧠</div>
              <h3 className="text-xl font-semibold mb-2">Cognitive Dashboard</h3>
              <p className="text-muted-foreground mb-4">
                질문을 입력하여 의도 분석 및 실행 계획 과정을 확인하세요
              </p>
              <div className="max-w-md mx-auto text-left space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    Intent Analysis: 사용자 의도 분석 결과 (IntentType, Confidence)
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    Execution Plan: 생성된 실행 계획 (Steps, Priority, Strategy)
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-sm text-muted-foreground">
                    Data Reuse: 이전 데이터 재사용 여부
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

function IntentAnalysisCard({ data }: { data: IntentAnalysisData }) {
  const display = INTENT_DISPLAY[data.intent_type]

  return (
    <Card className="p-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">🔍 Intent Analysis</h3>
          <span className="text-xs text-muted-foreground">{data.timestamp}</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Intent Type */}
          <div className="p-3 bg-secondary/20 rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">의도 분류</div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">{display?.icon || "❓"}</span>
              <div>
                <div className="font-semibold">{display?.label || data.intent_type}</div>
                <div className="text-xs text-muted-foreground">{data.intent_type}</div>
              </div>
            </div>
          </div>

          {/* Confidence */}
          <div className="p-3 bg-secondary/20 rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">신뢰도</div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold">{(data.confidence * 100).toFixed(0)}%</span>
                <span className={`text-xs font-semibold ${
                  data.confidence >= 0.8 ? "text-green-600" :
                  data.confidence >= 0.5 ? "text-yellow-600" :
                  "text-red-600"
                }`}>
                  {data.confidence >= 0.8 ? "높음" :
                   data.confidence >= 0.5 ? "보통" :
                   "낮음"}
                </span>
              </div>
              <ProgressBar value={data.confidence * 100} size="sm" showLabel={false} />
            </div>
          </div>
        </div>

        {/* Keywords */}
        {data.keywords && data.keywords.length > 0 && (
          <div className="p-3 bg-secondary/20 rounded-lg">
            <div className="text-xs text-muted-foreground mb-2">추출된 키워드</div>
            <div className="flex flex-wrap gap-2">
              {data.keywords.map((keyword, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 text-xs font-medium bg-primary/10 text-primary rounded"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Reasoning */}
        {data.reasoning && (
          <div className="p-3 bg-secondary/20 rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">판단 근거</div>
            <div className="text-sm">{data.reasoning}</div>
          </div>
        )}
      </div>
    </Card>
  )
}

function ExecutionPlanCard({ data }: { data: ExecutionPlanData }) {
  return (
    <Card className="p-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">📋 Execution Plan</h3>
          <div className="flex items-center gap-4">
            <div className="text-xs">
              <span className="text-muted-foreground">Strategy:</span>{" "}
              <span className="font-semibold">{data.execution_strategy}</span>
            </div>
            <div className="text-xs">
              <span className="text-muted-foreground">예상 시간:</span>{" "}
              <span className="font-semibold">{data.estimated_total_time}초</span>
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-2">
          {data.execution_steps.map((step, idx) => {
            const agentDisplay = AGENT_DISPLAY[step.agent_name] || { label: step.agent_name, icon: "🤖" }

            return (
              <div
                key={step.step_id}
                className="p-3 bg-secondary/20 rounded-lg border border-border"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{agentDisplay.icon}</span>
                      <div>
                        <div className="font-semibold text-sm">{step.task}</div>
                        <div className="text-xs text-muted-foreground">{step.description}</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-1 rounded bg-primary/10 text-primary font-medium">
                      Priority {step.priority}
                    </span>
                    <span className="text-xs px-2 py-1 rounded bg-secondary text-muted-foreground">
                      {step.team}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Strategy Details */}
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="text-xs text-blue-700 dark:text-blue-400">
            <strong>실행 전략:</strong>{" "}
            {data.execution_strategy === "sequential"
              ? "순차 실행 - 각 팀이 순서대로 실행됩니다"
              : "병렬 실행 - 여러 팀이 동시에 실행됩니다"}
          </div>
        </div>
      </div>
    </Card>
  )
}

function DataReuseCard({ data }: { data: DataReuseInfo }) {
  return (
    <Card className="p-4 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">♻️</span>
          <h3 className="text-lg font-semibold text-green-700 dark:text-green-400">
            Data Reuse Optimization
          </h3>
        </div>

        <div className="space-y-2">
          <div className="text-sm text-green-700 dark:text-green-400">
            이전 대화에서 검색 결과를 재사용하여 성능을 최적화했습니다.
          </div>

          <div className="flex flex-wrap gap-2">
            {data.reused_teams.map((team, idx) => {
              const display = AGENT_DISPLAY[team] || { label: team, icon: "🤖" }
              return (
                <div
                  key={idx}
                  className="px-3 py-2 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg flex items-center gap-2"
                >
                  <span>{display.icon}</span>
                  <span className="text-sm font-medium text-green-700 dark:text-green-400">
                    {display.label}
                  </span>
                  <span className="text-xs text-green-600 dark:text-green-500">재사용</span>
                </div>
              )
            })}
          </div>

          {data.reused_from_message !== undefined && (
            <div className="text-xs text-green-600 dark:text-green-500">
              메시지 #{data.reused_from_message}에서 재사용
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
