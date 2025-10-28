"use client"

import React from "react"
import { Card } from "@/components/ui/card"
import { ProgressBar } from "@/components/ui/progress-bar"
import type { ExecutionStep, ExecutionPlan } from "@/types/execution"
import type {
  ThreeLayerProgressData,
  SupervisorPhase,
  AgentProgress,
  AgentStep
} from "@/types/progress"
import {
  AGENT_ICONS,
  AGENT_DISPLAY_NAMES,
  STEP_STATUS_COLORS,
  STEP_STATUS_ICONS
} from "@/types/progress"

// ============================================================================
// Props Definition
// ============================================================================

// 기존 방식 (하위 호환)
export type ProgressStage = "dispatch" | "analysis" | "executing" | "generating"

export interface LegacyProgressProps {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
  reusedTeams?: string[]
}

// 새 방식 (3-Layer)
export interface ThreeLayerProgressProps {
  progressData: ThreeLayerProgressData
}

// 통합 Props (하나만 제공하면 됨)
export type ProgressContainerProps =
  | ({ mode: "legacy" } & LegacyProgressProps)
  | ({ mode: "three-layer" } & ThreeLayerProgressProps)

// ============================================================================
// Supervisor Phase Configuration (Layer 1)
// ============================================================================

const SUPERVISOR_PHASES: Record<SupervisorPhase, {
  title: string
  range: [number, number]
  description: string
  icon: string
  estimatedTime: string
}> = {
  dispatching: {
    title: "접수",
    range: [0, 10],
    description: "질문을 접수하고 있습니다",
    icon: "📥",
    estimatedTime: "약 1초"
  },
  analyzing: {
    title: "분석",
    range: [10, 30],
    description: "질문을 분석하고 계획을 수립하고 있습니다",
    icon: "🔍",
    estimatedTime: "약 6초"
  },
  executing: {
    title: "실행",
    range: [30, 75],
    description: "작업을 실행하고 있습니다",
    icon: "⚙️",
    estimatedTime: "약 3초"
  },
  finalizing: {
    title: "완료",
    range: [75, 100],
    description: "결과를 정리하고 있습니다",
    icon: "✅",
    estimatedTime: "약 10초"
  }
}

// Legacy Stage Config (기존 호환)
const LEGACY_STAGE_CONFIG = {
  dispatch: {
    index: 0,
    title: "출동 중",
    spinner: "/animation/spinner/1_execution-plan_spinner.gif"
  },
  analysis: {
    index: 1,
    title: "분석 중",
    spinner: "/animation/spinner/2_execution-progress_spinner.gif"
  },
  executing: {
    index: 2,
    title: "실행 중",
    spinner: "/animation/spinner/3_execution-progress_spinner.gif"
  },
  generating: {
    index: 3,
    title: "답변 작성 중",
    spinner: "/animation/spinner/4_response-generating_spinner.gif"
  }
} as const

// ============================================================================
// Main Container Component
// ============================================================================

export function ProgressContainer(props: ProgressContainerProps) {
  // 3-Layer 모드
  if (props.mode === "three-layer") {
    return <ThreeLayerProgress progressData={props.progressData} />
  }

  // Legacy 모드 (기존 방식)
  return <LegacyProgress {...props} />
}

// ============================================================================
// 3-Layer Progress Component
// ============================================================================

function ThreeLayerProgress({ progressData }: { progressData: ThreeLayerProgressData }) {
  const {
    supervisorPhase,
    supervisorProgress,
    activeAgents
  } = progressData

  return (
    <div className="w-full max-w-3xl">
      <Card className="p-3 bg-card border">
        {/* Layer 1: Supervisor Progress Bar */}
        <SupervisorProgressBar
          phase={supervisorPhase}
          progress={supervisorProgress}
        />

        {/* Layer 2: Agent Steps */}
        {activeAgents && activeAgents.length > 0 && (
          <div className="mt-3 space-y-2">
            {activeAgents.map(agent => (
              <AgentStepsCard
                key={agent.agentName}
                agentProgress={agent}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

// ============================================================================
// Layer 1: Supervisor Progress Bar Component
// ============================================================================

function SupervisorProgressBar({
  phase,
  progress
}: {
  phase: SupervisorPhase
  progress: number
}) {
  const allPhases = Object.entries(SUPERVISOR_PHASES) as [SupervisorPhase, typeof SUPERVISOR_PHASES[SupervisorPhase]][]
  const currentPhaseIndex = allPhases.findIndex(([key]) => key === phase)

  return (
    <div>
      {/* 전체 진행률 바 */}
      <div className="mb-3 p-2 bg-primary/5 rounded-lg border border-primary/20">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-primary">전체 진행률</span>
          <span className="text-xs font-bold text-primary">
            {Math.round(progress)}%
          </span>
        </div>
        <ProgressBar
          value={progress}
          size="md"
          variant="default"
          showLabel={false}
        />
      </div>

      {/* 4-Phase Steps */}
      <div className="grid grid-cols-4 gap-2 mb-2">
        {allPhases.map(([key, config], idx) => {
          const isCompleted = idx < currentPhaseIndex
          const isCurrent = idx === currentPhaseIndex
          const isPending = idx > currentPhaseIndex

          return (
            <div
              key={key}
              className={`
                p-2 rounded-lg border text-center transition-all duration-300
                ${isCompleted
                  ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                  : isCurrent
                  ? "bg-primary/10 border-primary scale-105"
                  : "bg-muted border-muted-foreground/20 opacity-60"
                }
              `}
            >
              <div className="text-xl mb-1">
                {isCompleted ? "✓" : isCurrent ? config.icon : "○"}
              </div>
              <div className={`text-xs font-medium ${isCurrent ? "text-primary" : ""}`}>
                {config.title}
              </div>
            </div>
          )
        })}
      </div>

      {/* 현재 Phase 설명 및 예상 시간 */}
      {SUPERVISOR_PHASES[phase] && (
        <div className="text-center py-1 space-y-0.5">
          <div className="text-xs text-muted-foreground">
            {SUPERVISOR_PHASES[phase].description}
          </div>
          <div className="text-xs text-muted-foreground/70 flex items-center justify-center gap-1">
            <span>⏱️</span>
            <span>{SUPERVISOR_PHASES[phase].estimatedTime} 소요 예상</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Layer 2: Agent Steps Card Component
// ============================================================================

function AgentStepsCard({ agentProgress }: { agentProgress: AgentProgress }) {
  const { agentName, agentType, steps, currentStepIndex, overallProgress, status, isReused } = agentProgress

  // Agent 아이콘 및 이름
  const agentIcon = (AGENT_ICONS as any)[agentType] || "🤖"
  const agentDisplayName = (AGENT_DISPLAY_NAMES as any)[agentType] || agentName

  return (
    <Card className={`p-3 border ${isReused ? "bg-green-50/50 dark:bg-green-900/10 border-green-200 dark:border-green-800" : "bg-secondary/20 border-border"}`}>
      {/* Agent 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{agentIcon}</span>
          <span className="font-semibold text-sm">{agentDisplayName}</span>
          {/* 🆕 재사용 표시 */}
          {isReused && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700 flex items-center gap-1">
              <span>♻️</span>
              <span>재사용</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isReused && (
            <span className="text-xs text-muted-foreground">
              Step {currentStepIndex + 1}/{steps.length}
            </span>
          )}
          {status === "running" && (
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          )}
          {isReused && status === "completed" && (
            <span className="text-xs text-green-600 dark:text-green-400">완료</span>
          )}
        </div>
      </div>

      {/* Agent 전체 진행률 */}
      <div className="mb-2">
        <ProgressBar value={overallProgress} size="sm" showLabel={false} />
      </div>

      {/* Step 목록 */}
      <div className="space-y-1">
        {steps.map((step, idx) => (
          <StepRow
            key={step.id}
            step={step}
            isActive={idx === currentStepIndex}
          />
        ))}
      </div>
    </Card>
  )
}

// ============================================================================
// Step Row Component
// ============================================================================

function StepRow({ step, isActive }: { step: AgentStep; isActive: boolean }) {
  const statusConfig = (STEP_STATUS_COLORS as any)[step.status]
  const statusIcon = (STEP_STATUS_ICONS as any)[step.status]

  return (
    <div
      className={`
        flex items-center gap-2 p-2 rounded border transition-all duration-200
        ${isActive
          ? `${statusConfig.bg} ${statusConfig.border} scale-105`
          : "bg-muted/30 border-transparent"
        }
      `}
    >
      {/* Status 아이콘 */}
      <span className={`text-base ${statusConfig.text}`}>
        {statusIcon}
      </span>

      {/* Step 이름 */}
      <span className={`flex-1 text-sm ${isActive ? "font-medium" : ""}`}>
        {step.name}
      </span>

      {/* HITL 표시 */}
      {step.isHitl && step.status === "in_progress" && (
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-orange-500 rounded-full animate-ping" />
          <span className="text-xs text-orange-600 dark:text-orange-400 font-medium">
            대기
          </span>
        </div>
      )}

      {/* 진행률 바 (in_progress && progress 있을 때) */}
      {step.status === "in_progress" && step.progress !== undefined && !step.isHitl && (
        <div className="w-16">
          <ProgressBar value={step.progress} size="sm" showLabel={false} />
        </div>
      )}

      {/* 에러 표시 */}
      {step.status === "failed" && step.error && (
        <span className="text-xs text-red-600 dark:text-red-400">
          실패
        </span>
      )}
    </div>
  )
}

// ============================================================================
// Legacy Progress Component (기존 방식 유지)
// ============================================================================

function LegacyProgress(props: LegacyProgressProps) {
  const { stage, plan, steps = [], responsePhase = "aggregation", reusedTeams = [] } = props

  const currentStage = LEGACY_STAGE_CONFIG[stage]
  const allStages = Object.values(LEGACY_STAGE_CONFIG)

  // 전체 프로세스 진행률 계산 (기존 로직)
  const calculateOverallProgress = (): number => {
    switch (stage) {
      case "dispatch":
        return 10

      case "analysis":
        if (plan && !plan.isLoading && plan.execution_steps && plan.execution_steps.length > 0) {
          return 40
        }
        return 25

      case "executing":
        const totalSteps = steps.length
        const completedSteps = steps.filter(s => s.status === "completed").length
        if (totalSteps > 0) {
          const executionProgress = (completedSteps / totalSteps) * 35
          return 40 + executionProgress
        }
        return 40

      case "generating":
        if (responsePhase === "response_generation") {
          return 90
        }
        return 80

      default:
        return 0
    }
  }

  const overallProgress = calculateOverallProgress()

  return (
    <div className="w-full max-w-3xl">
      <Card className="p-3 bg-card border">
        {/* 전체 프로세스 진행률 */}
          <div className="mb-3 p-2 bg-primary/5 rounded-lg border border-primary/20">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-primary">전체 진행률</span>
              <span className="text-xs font-bold text-primary">{Math.round(overallProgress)}%</span>
            </div>
            <ProgressBar
              value={overallProgress}
              size="md"
              variant="default"
              showLabel={false}
            />
          </div>

          {/* 상단: 4-Stage Spinner Bar */}
          <div className="grid grid-cols-4 mb-2">
            {allStages.map((s, idx) => (
              <div key={idx} className="flex flex-col items-center justify-start">
                <div
                  className={`
                    w-full aspect-square transition-all duration-150 ease-in-out
                    ${
                      idx === currentStage.index
                        ? "opacity-100 grayscale-0 scale-110"
                        : "opacity-40 grayscale scale-90"
                    }
                  `}
                >
                  <img
                    src={s.spinner}
                    alt={s.title}
                    className="w-full h-full object-contain"
                  />
                </div>
                <div
                  className={`
                    font-bold transition-all duration-150 leading-none
                    ${
                      idx === currentStage.index
                        ? "text-2xl text-foreground opacity-100 scale-110 -mt-4"
                        : "text-base text-muted-foreground opacity-40 scale-75 -mt-3"
                    }
                  `}
                  style={{ fontFamily: "'Hi Melody', cursive" }}
                >
                  {s.title}
                </div>
              </div>
            ))}
          </div>

          {/* 하단: Content Area (Stage별 변경) */}
          <div className="min-h-[120px]">
            {stage === "dispatch" && <DispatchContent />}
            {stage === "analysis" && <AnalysisContent plan={plan} />}
            {stage === "executing" && <ExecutingContent steps={steps} reusedTeams={reusedTeams} />}
            {stage === "generating" && <GeneratingContent phase={responsePhase} />}
          </div>
        </Card>
    </div>
  )
}

// Legacy Content Components (기존 유지)
function DispatchContent() {
  return (
    <div className="text-center py-4">
      <div className="animate-pulse">
        <div className="text-base font-semibold">질문을 접수했습니다</div>
        <div className="text-sm text-muted-foreground mt-1">
          잠시만 기다려주세요...
        </div>
      </div>
    </div>
  )
}

function AnalysisContent({ plan }: { plan?: ExecutionPlan }) {
  return (
    <div className="space-y-3">
      <div className="text-center">
        <div className="text-base font-semibold">질문을 분석하고 있습니다</div>
      </div>

      {plan && !plan.isLoading && plan.execution_steps && plan.execution_steps.length > 0 && (
        <div className="space-y-2">
          <div className="p-3 bg-secondary/30 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">분석 완료</span>
              <span className="text-sm text-muted-foreground">{plan.intent}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">신뢰도:</span>
              <ProgressBar
                value={(plan.confidence || 0) * 100}
                size="sm"
                variant="default"
              />
              <span className="text-xs font-medium">
                {((plan.confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-medium">작업 계획:</div>
            {plan.execution_steps.map((step, idx) => (
              <div
                key={step.step_id || idx}
                className="flex items-center gap-3 p-2 bg-muted/50 rounded"
              >
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium">
                  {idx + 1}
                </div>
                <div className="text-sm">{step.task || step.description}</div>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-border">
            <p className="text-xs text-muted-foreground text-center">
              곧 작업을 시작합니다...
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

function ExecutingContent({ steps, reusedTeams = [] }: { steps: ExecutionStep[]; reusedTeams?: string[] }) {
  const reusedSteps: ExecutionStep[] = reusedTeams.map((teamName, idx) => ({
    step_id: `reused-${teamName}-${idx}`,
    task: `${teamName.charAt(0).toUpperCase() + teamName.slice(1)} Team`,
    description: `${teamName} 데이터 재사용`,
    status: "completed" as const,
    agent: teamName,
    isReused: true
  }))

  const allSteps = [...reusedSteps, ...steps]
  const totalSteps = allSteps.length
  const completedSteps = allSteps.filter((s) => s.status === "completed").length
  const failedSteps = allSteps.filter((s) => s.status === "failed").length
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="space-y-3">
      <div className="p-3 bg-secondary/20 rounded-lg border border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-base">전체 작업 진행률</span>
          <span className="text-sm font-medium text-primary">
            {completedSteps}/{totalSteps} 완료
          </span>
        </div>
        <ProgressBar
          value={overallProgress}
          size="lg"
          variant={failedSteps > 0 ? "warning" : "default"}
          showLabel={true}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {allSteps.map((step) => (
          <AgentCard key={step.step_id} step={step} />
        ))}
      </div>

      {failedSteps > 0 && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-xs text-red-700 dark:text-red-400">
            {failedSteps}개의 작업이 실패했습니다. 일부 정보가 누락될 수 있습니다.
          </p>
        </div>
      )}
    </div>
  )
}

function AgentCard({ step }: { step: ExecutionStep }) {
  const statusConfig = {
    pending: {
      icon: "○",
      color: "text-muted-foreground",
      bg: "bg-muted",
      borderColor: "border-muted-foreground/20"
    },
    in_progress: {
      icon: "●",
      color: "text-primary",
      bg: "bg-primary/10",
      borderColor: "border-primary"
    },
    completed: {
      icon: "✓",
      color: "text-green-600",
      bg: "bg-green-50 dark:bg-green-900/20",
      borderColor: "border-green-200 dark:border-green-800"
    },
    failed: {
      icon: "✗",
      color: "text-red-600",
      bg: "bg-red-50 dark:bg-red-900/20",
      borderColor: "border-red-200 dark:border-red-800"
    },
    skipped: {
      icon: "⊘",
      color: "text-yellow-600",
      bg: "bg-yellow-50 dark:bg-yellow-900/20",
      borderColor: "border-yellow-200 dark:border-yellow-800"
    }
  }

  const config = statusConfig[step.status] || statusConfig.pending

  return (
    <div className={`p-3 rounded-lg border ${config.bg} ${config.borderColor}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xl ${config.color}`}>{config.icon}</span>
        <span className="font-medium text-sm">{step.task}</span>
        {step.isReused && (
          <span className="ml-auto px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
            ♻️ 재사용
          </span>
        )}
      </div>
      <div className="text-xs text-muted-foreground mb-2">{step.description}</div>

      {step.status === "in_progress" && step.progress !== undefined && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">진행률</span>
            <span className="font-medium text-primary">{Math.round(step.progress)}%</span>
          </div>
          <ProgressBar
            value={step.progress}
            size="md"
            variant="default"
            showLabel={false}
          />
        </div>
      )}
    </div>
  )
}

function GeneratingContent({ phase }: { phase?: "aggregation" | "response_generation" }) {
  const statusConfig = {
    pending: {
      icon: "○",
      color: "text-muted-foreground",
      bg: "bg-muted",
      borderColor: "border-muted-foreground/20"
    },
    in_progress: {
      icon: "●",
      color: "text-primary",
      bg: "bg-primary/10",
      borderColor: "border-primary"
    },
    completed: {
      icon: "✓",
      color: "text-green-600",
      bg: "bg-green-50 dark:bg-green-900/20",
      borderColor: "border-green-200 dark:border-green-800"
    }
  }

  const steps: Array<{ id: string; label: string; status: "pending" | "in_progress" | "completed" }> = [
    { id: "collect", label: "데이터 수집 완료", status: "completed" },
    {
      id: "organize",
      label: "정보 정리 중",
      status: phase === "aggregation" ? "in_progress" : "completed"
    },
    {
      id: "generate",
      label: "최종 답변 생성 중",
      status: phase === "response_generation" ? "in_progress" : "pending"
    }
  ]

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {steps.map((step) => {
          const config = statusConfig[step.status]
          return (
            <div
              key={step.id}
              className={`p-2 rounded-lg border ${config.bg} ${config.borderColor}`}
            >
              <div className="flex items-center gap-2">
                <span className={`text-lg ${config.color}`}>{config.icon}</span>
                <span className="font-medium text-xs">{step.label}</span>
              </div>
            </div>
          )
        })}
      </div>

      <div className="text-center text-xs text-muted-foreground pt-2 border-t border-border">
        잠시만 기다려주세요. 최적의 답변을 준비하고 있습니다.
      </div>
    </div>
  )
}
