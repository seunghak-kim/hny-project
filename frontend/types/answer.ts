/**
 * Answer-related type definitions
 * 답변 관련 타입 정의
 */

/**
 * 답변 섹션 구조
 * UI에서 표시될 각 섹션의 정보
 */
export interface AnswerSection {
  /** 섹션 제목 */
  title: string

  /** 섹션 내용 (텍스트 또는 리스트) */
  content: string | string[]

  /** 섹션 아이콘 이름 */
  icon?: string

  /** 우선순위 (표시 순서 및 스타일) */
  priority?: "high" | "medium" | "low"

  /** 확장/축소 가능 여부 */
  expandable?: boolean

  /** 콘텐츠 타입 */
  type?: "text" | "checklist" | "warning"
}

/**
 * 답변 메타데이터
 * 답변의 부가 정보
 */
export interface AnswerMetadata {
  /** 신뢰도 (0.0 ~ 1.0) */
  confidence: number

  /** 참고 자료 목록 */
  sources: string[]

  /** 의도 타입 */
  intent_type: string
}

/**
 * 구조화된 답변 (LLM 응답)
 * response_synthesis.txt 프롬프트의 JSON 형식과 일치
 */
export interface StructuredAnswer {
  /** 핵심 답변 */
  answer: string

  /** 세부 정보 */
  details: {
    /** 법적 근거 */
    legal_basis?: string

    /** 데이터 분석 결과 */
    data_analysis?: string

    /** 고려사항 리스트 */
    considerations?: string[]
  }

  /** 추천사항 리스트 */
  recommendations: string[]

  /** 참고 자료 */
  sources: string[]

  /** 신뢰도 */
  confidence: number

  /** 추가 정보 */
  additional_info?: string
}

/**
 * 구조화된 데이터 (Frontend 표시용)
 * Backend에서 처리된 최종 데이터
 */
export interface StructuredData {
  /** UI 섹션 리스트 */
  sections: AnswerSection[]

  /** 메타데이터 */
  metadata: AnswerMetadata

  /** 원본 JSON (디버깅용) */
  raw?: StructuredAnswer
}

/**
 * 답변 응답 타입
 * WebSocket으로 전달되는 최종 응답
 */
export interface AnswerResponse {
  /** 응답 타입 */
  type: "answer" | "error" | "guidance"

  /** 텍스트 답변 (하위 호환성) */
  answer?: string

  /** 구조화된 데이터 */
  structured_data?: StructuredData

  /** 사용된 팀 목록 */
  teams_used?: string[]

  /** 원본 데이터 */
  data?: Record<string, any>

  /** 에러 메시지 (type이 error인 경우) */
  message?: string
}

/**
 * 의도 타입 enum
 */
export enum IntentType {
  LEGAL_CONSULT = "legal_consult",
  MARKET_INQUIRY = "market_inquiry",
  LOAN_CONSULT = "loan_consult",
  CONTRACT_REVIEW = "contract_review",
  CONTRACT_CREATION = "contract_creation",
  COMPREHENSIVE = "comprehensive",
  RISK_ANALYSIS = "risk_analysis",
  UNCLEAR = "unclear",
  IRRELEVANT = "irrelevant",
  UNKNOWN = "unknown"
}

/**
 * 의도 타입 한글 레이블 매핑
 */
export const INTENT_LABELS: Record<string, string> = {
  legal_consult: "법률 상담",
  market_inquiry: "시세 조회",
  loan_consult: "대출 상담",
  contract_review: "계약서 검토",
  contract_creation: "계약서 작성",
  comprehensive: "종합 분석",
  risk_analysis: "리스크 분석",
  unclear: "명확화 필요",
  irrelevant: "기능 외 질문",
  unknown: "분석 중"
}