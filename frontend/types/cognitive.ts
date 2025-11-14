/**
 * Cognitive Dashboard Types
 * 의도 분석 및 계획 수립 과정 관련 타입 정의
 */

// ============================================================================
// Intent Analysis Types
// ============================================================================

export type IntentType =
  | "LEGAL_CONSULT"
  | "MARKET_INQUIRY"
  | "LOAN_CONSULT"
  | "CONTRACT_CREATION"
  | "CONTRACT_REVIEW"
  | "COMPREHENSIVE"
  | "RISK_ANALYSIS"
  | "UNCLEAR"
  | "IRRELEVANT"
  | "ERROR"

export interface IntentAnalysisData {
  intent_type: IntentType
  confidence: number
  keywords: string[]
  reasoning: string
  entities?: Record<string, any>
  timestamp?: string
}

// ============================================================================
// Agent Selection Types
// ============================================================================

export type AgentSelectionLayer = "keyword_filter" | "primary_llm" | "simplified_prompt" | "safe_defaults"

export interface AgentSelectionData {
  suggested_agents: string[]
  selection_layer: AgentSelectionLayer
  reasoning?: string
  timestamp?: string
}

// ============================================================================
// Execution Plan Types
// ============================================================================

export type ExecutionStrategy = "sequential" | "parallel"

export interface ExecutionStepData {
  step_id: string
  step_type: string
  agent_name: string
  team: string
  priority: number
  task: string
  description: string
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped"
  progress_percentage?: number
  started_at?: string
  completed_at?: string
  result?: any
  error?: string
}

export interface ExecutionPlanData {
  execution_steps: ExecutionStepData[]
  execution_strategy: ExecutionStrategy
  estimated_total_time: number
  parallel_groups?: number[][]
}

// ============================================================================
// Memory Types
// ============================================================================

export interface MemoryTierData {
  tier: "short" | "mid" | "long"
  count: number
  sessions?: any[]
}

export interface MemoryLoadData {
  short_term: MemoryTierData
  mid_term: MemoryTierData
  long_term: MemoryTierData
  user_preferences?: Record<string, any>
  total_count: number
}

// ============================================================================
// Data Reuse Types
// ============================================================================

export interface DataReuseInfo {
  reused: boolean
  reused_teams: string[]
  reused_from_message?: number
  timestamp?: string
}

// ============================================================================
// Cognitive Dashboard State
// ============================================================================

export interface CognitiveState {
  query?: string
  intent_analysis?: IntentAnalysisData
  agent_selection?: AgentSelectionData
  execution_plan?: ExecutionPlanData
  memory_load?: MemoryLoadData
  data_reuse?: DataReuseInfo
  phase: "idle" | "analyzing" | "planning" | "completed"
  timestamp?: string
}

// ============================================================================
// Display Constants
// ============================================================================

export const INTENT_TYPE_DISPLAY: Record<IntentType, { label: string; icon: string; color: string }> = {
  LEGAL_CONSULT: { label: "법률 상담", icon: "⚖️", color: "blue" },
  MARKET_INQUIRY: { label: "시세 조회", icon: "📊", color: "green" },
  LOAN_CONSULT: { label: "대출 상담", icon: "💰", color: "yellow" },
  CONTRACT_CREATION: { label: "계약서 작성", icon: "📝", color: "purple" },
  CONTRACT_REVIEW: { label: "계약서 검토", icon: "🔍", color: "indigo" },
  COMPREHENSIVE: { label: "종합 상담", icon: "🎯", color: "pink" },
  RISK_ANALYSIS: { label: "위험 분석", icon: "⚠️", color: "red" },
  UNCLEAR: { label: "불명확", icon: "❓", color: "gray" },
  IRRELEVANT: { label: "관련 없음", icon: "🚫", color: "gray" },
  ERROR: { label: "오류", icon: "❌", color: "red" }
}

export const AGENT_NAME_DISPLAY: Record<string, { label: string; icon: string }> = {
  search_team: { label: "검색 팀", icon: "🔍" },
  analysis_team: { label: "분석 팀", icon: "📊" },
  document_team: { label: "문서 팀", icon: "📝" }
}

export const SELECTION_LAYER_DISPLAY: Record<AgentSelectionLayer, { label: string; color: string }> = {
  keyword_filter: { label: "키워드 필터", color: "green" },
  primary_llm: { label: "LLM 추천", color: "blue" },
  simplified_prompt: { label: "간소화 프롬프트", color: "yellow" },
  safe_defaults: { label: "기본값", color: "gray" }
}
