/**
 * Execution Step Types
 * Backend의 ExecutionStepState와 동일한 구조 (간소화됨)
 */

export type StepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed"
  | "skipped"

export type StepType = "planning" | "search" | "document" | "analysis"

export interface ExecutionStep {
  // 식별 정보 (4개)
  step_id: string
  step_type?: StepType
  agent_name?: string
  team?: string

  // 작업 정보 (2개)
  task: string
  description: string

  // 상태 추적 (2개)
  status: StepStatus
  progress_percentage?: number

  // 타이밍 (2개)
  started_at?: string | null
  completed_at?: string | null

  // 결과/에러 (2개)
  result?: Record<string, any> | null
  error?: string | null

  // 🆕 Option A: 재사용 플래그
  isReused?: boolean
  agent?: string  // Legacy field for compatibility
  progress?: number  // Legacy field for compatibility
}

export interface ExecutionPlan {
  intent: string
  confidence: number
  execution_steps: ExecutionStep[]
  execution_strategy: "sequential" | "parallel" | "pipeline"
  estimated_total_time: number
  keywords?: string[]
  isLoading?: boolean  // 로딩 상태 플래그
}

export interface ExecutionProgress {
  totalSteps: number
  completedSteps: number
  currentStep?: ExecutionStep
  overallProgress: number            // 0-100
  elapsedTime: number                // 밀리초
  estimatedTimeRemaining: number     // 밀리초
}
