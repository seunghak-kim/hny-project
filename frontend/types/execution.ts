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

// ============================================================================
// Execution Dashboard Types
// ============================================================================

export interface TeamExecutionState {
  team_name: string
  status: "idle" | "running" | "completed" | "failed"
  steps: TeamStep[]
  current_step_index: number
  overall_progress: number
  tools_used?: string[]
  llm_calls?: LLMCallInfo[]
  start_time?: string
  end_time?: string
  total_time?: number  // seconds
}

export interface TeamStep {
  step_name: string
  status: StepStatus
  progress?: number
  duration?: number  // seconds
  started_at?: string
  completed_at?: string
  error?: string
}

export interface LLMCallInfo {
  llm_id: string
  prompt_name: string
  started_at: string
  completed_at?: string
  duration?: number  // seconds
  tokens_used?: number
  success: boolean
  error?: string
}

export interface ResponseGenerationState {
  phase: "idle" | "aggregation" | "response_generation" | "validation" | "completed"
  current_phase_progress: number
  start_time?: string
  end_time?: string
}

export interface ExecutionDashboardState {
  query?: string
  active_teams: TeamExecutionState[]
  response_generation?: ResponseGenerationState
  performance_metrics?: PerformanceMetrics
  status: "idle" | "executing" | "generating" | "completed" | "error"
}

export interface PerformanceMetrics {
  total_execution_time: number  // seconds
  total_llm_calls: number
  total_tokens_used: number
  avg_llm_call_duration: number  // seconds
  team_durations: Record<string, number>  // team name -> duration (seconds)
}

// Display Constants
export const TEAM_DISPLAY_INFO: Record<string, { label: string; icon: string; color: string }> = {
  search: { label: "검색 팀", icon: "🔍", color: "blue" },
  analysis: { label: "분석 팀", icon: "📊", color: "green" },
  document: { label: "문서 팀", icon: "📝", color: "purple" }
}

export const TEAM_STEP_NAMES: Record<string, string[]> = {
  search: ["prepare", "route", "search", "aggregate", "finalize"],
  analysis: ["prepare", "analyze", "finalize"],
  document: ["prepare", "plan", "verify", "input", "review", "generate", "confirm"]
}
