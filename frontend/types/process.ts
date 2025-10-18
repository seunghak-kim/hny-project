/**
 * Process Flow Types
 * Backend 처리 과정 시각화를 위한 타입 정의
 */

export type ProcessStep =
  | "idle"           // 대기 상태
  | "planning"       // 계획 수립 중
  | "executing"      // 작업 실행 중
  | "searching"      // 정보 검색 중
  | "analyzing"      // 데이터 분석 중
  | "generating"     // 답변 생성 중
  | "complete"       // 완료
  | "error"          // 에러 발생

export type AgentType =
  | "analysis"       // 분석 에이전트
  | "verification"   // 검증 에이전트
  | "consultation"   // 상담 에이전트

export interface ProcessState {
  /** 현재 처리 단계 */
  step: ProcessStep

  /** 활성화된 에이전트 타입 */
  agentType: AgentType | null

  /** 사용자에게 표시할 메시지 */
  message: string

  /** 진행률 (0-100, 선택적) */
  progress?: number

  /** 처리 시작 시간 (타임스탬프) */
  startTime?: number

  /** 에러 정보 (에러 발생 시) */
  error?: string
}

export interface ProcessFlowProps {
  /** ProcessFlow 표시 여부 */
  isVisible: boolean

  /** 현재 프로세스 상태 */
  state: ProcessState

  /** 취소 버튼 클릭 핸들러 (선택적) */
  onCancel?: () => void
}

/**
 * 단계별 기본 메시지
 */
export const STEP_MESSAGES: Record<ProcessStep, string> = {
  idle: "",
  planning: "계획을 수립하고 있습니다...",
  executing: "작업을 실행하고 있습니다...",
  searching: "관련 정보를 검색하고 있습니다...",
  analyzing: "데이터를 분석하고 있습니다...",
  generating: "답변을 생성하고 있습니다...",
  complete: "처리가 완료되었습니다",
  error: "오류가 발생했습니다"
}

/**
 * 에이전트별 표시 이름
 */
export const AGENT_NAMES: Record<AgentType, string> = {
  analysis: "분석 에이전트",
  verification: "검증 에이전트",
  consultation: "상담 에이전트"
}
