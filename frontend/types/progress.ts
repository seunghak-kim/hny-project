/**
 * 3-Layer Progress System Type Definitions
 *
 * Layer 1: Supervisor Phase (공통)
 * Layer 2: Agent Steps (Agent별 동적)
 * Layer 3: Task Details (선택적)
 */

// ============================================================================
// Layer 1: Supervisor Phase
// ============================================================================

/**
 * Supervisor Phase
 * 모든 질의응답에 공통적으로 적용되는 최상위 단계
 */
export type SupervisorPhase = "dispatching" | "analyzing" | "executing" | "finalizing"

/**
 * Supervisor Phase 설정
 */
export interface SupervisorPhaseConfig {
  title: string
  range: [number, number]  // [min%, max%]
  description: string
  icon?: string
}

// ============================================================================
// Layer 2: Agent Steps
// ============================================================================

/**
 * Agent Step 상태
 */
export type StepStatus = "pending" | "in_progress" | "completed" | "failed" | "skipped"

/**
 * HITL 타입
 */
export type HitlType = "form_input" | "approval" | "review" | "confirmation"

/**
 * Agent Step
 * 각 Agent가 정의하는 세부 실행 단계
 */
export interface AgentStep {
  id: string
  name: string
  status: StepStatus

  // HITL 관련
  isHitl?: boolean
  hitlType?: HitlType

  // 진행 상태
  progress?: number  // 0-100
  estimatedTime?: number  // seconds

  // 추가 정보
  metadata?: Record<string, any>
  error?: string  // status === "failed"일 때
}

/**
 * Agent Progress
 * 특정 Agent의 전체 진행 상태
 */
export interface AgentProgress {
  agentName: string
  agentType: string  // "search" | "document" | "analysis" | "contract_review" | ...

  steps: AgentStep[]
  currentStepIndex: number
  totalSteps: number

  overallProgress: number  // 0-100 (Agent 전체 진행률)

  // 상태
  status: "idle" | "running" | "completed" | "failed"
  startTime?: string  // ISO timestamp
  endTime?: string    // ISO timestamp

  // 데이터 재사용 플래그
  isReused?: boolean  // 이전 결과 재사용 여부
}

// ============================================================================
// Layer 3: Task Details (선택적)
// ============================================================================

/**
 * Task Detail
 * Step 내부의 세부 작업 (필요시만 사용)
 */
export interface TaskDetail {
  id: string
  name: string
  status: "pending" | "in_progress" | "completed"
  progress?: number  // 0-100
  metadata?: Record<string, any>
}

/**
 * Expanded Step
 * Task Details를 포함한 확장된 Step 정보
 */
export interface ExpandedStep extends AgentStep {
  tasks?: TaskDetail[]
}

// ============================================================================
// 통합 Progress Data
// ============================================================================

/**
 * 3-Layer Progress Data
 * 전체 Progress 시스템의 데이터 구조
 */
export interface ThreeLayerProgressData {
  // Layer 1: Supervisor Phase
  supervisorPhase: SupervisorPhase
  supervisorProgress: number  // 0-100

  // Layer 2: Active Agents
  activeAgents: AgentProgress[]

  // Layer 3: Expanded Step (선택적)
  expandedStepId?: string
  taskDetails?: TaskDetail[]

  // 메타데이터
  totalEstimatedTime?: number  // 전체 예상 소요 시간 (초)
  elapsedTime?: number         // 경과 시간 (초)
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

/**
 * Supervisor Phase 변경 메시지
 */
export interface SupervisorPhaseChangeMessage {
  type: "supervisor_phase_change"
  supervisorPhase: SupervisorPhase
  supervisorProgress: number
  description?: string
}

/**
 * Agent Steps 초기화 메시지
 */
export interface AgentStepsInitializedMessage {
  type: "agent_steps_initialized"
  agentName: string
  agentType: string
  steps: AgentStep[]
  currentStepIndex: number
  totalSteps: number
}

/**
 * Agent Step 진행 메시지
 */
export interface AgentStepProgressMessage {
  type: "agent_step_progress"
  agentName: string
  stepId: string
  status: StepStatus
  progress?: number
  metadata?: Record<string, any>
}

/**
 * Agent Step 완료 메시지
 */
export interface AgentStepCompleteMessage {
  type: "agent_step_complete"
  agentName: string
  stepId: string
  status: "completed" | "failed"
  result?: any
  error?: string
}

/**
 * Task Detail 업데이트 메시지 (Layer 3)
 */
export interface TaskDetailUpdateMessage {
  type: "task_detail_update"
  agentName: string
  stepId: string
  tasks: TaskDetail[]
}

// ============================================================================
// 유틸리티 타입
// ============================================================================

/**
 * Agent Icon Mapping
 */
export const AGENT_ICONS: Record<string, string> = {
  search: "🔍",
  document: "📝",
  analysis: "📊",
  contract_review: "📋",
  legal_consult: "⚖️",
  property_inspect: "🏠",
  loan_calc: "💰",
  tax_plan: "💼",
  market_analysis: "📈",
  risk_assessment: "⚠️"
}

/**
 * Agent Display Names
 */
export const AGENT_DISPLAY_NAMES: Record<string, string> = {
  search: "정보 수집",
  document: "문서 작성",
  analysis: "분석 중",
  contract_review: "계약서 검토",
  legal_consult: "법률 자문",
  property_inspect: "매물 조사",
  loan_calc: "대출 계산",
  tax_plan: "세금 계획",
  market_analysis: "시장 분석",
  risk_assessment: "리스크 평가"
}

/**
 * Step Status 색상
 */
export const STEP_STATUS_COLORS: Record<StepStatus, { bg: string; border: string; text: string }> = {
  pending: {
    bg: "bg-muted",
    border: "border-muted-foreground/20",
    text: "text-muted-foreground"
  },
  in_progress: {
    bg: "bg-primary/10",
    border: "border-primary",
    text: "text-primary"
  },
  completed: {
    bg: "bg-green-50 dark:bg-green-900/20",
    border: "border-green-200 dark:border-green-800",
    text: "text-green-600 dark:text-green-400"
  },
  failed: {
    bg: "bg-red-50 dark:bg-red-900/20",
    border: "border-red-200 dark:border-red-800",
    text: "text-red-600 dark:text-red-400"
  },
  skipped: {
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    border: "border-yellow-200 dark:border-yellow-800",
    text: "text-yellow-600 dark:text-yellow-400"
  }
}

/**
 * Step Status 아이콘
 */
export const STEP_STATUS_ICONS: Record<StepStatus, string> = {
  pending: "○",
  in_progress: "●",
  completed: "✓",
  failed: "✗",
  skipped: "⊘"
}
