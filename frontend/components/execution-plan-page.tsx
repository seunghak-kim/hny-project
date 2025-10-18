"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Target, Loader2 } from "lucide-react"
import type { ExecutionPlan } from "@/types/execution"

interface ExecutionPlanPageProps {
  plan: ExecutionPlan
}

/**
 * 실행 계획 표시 페이지
 *
 * 사용자에게 어떤 작업들이 수행될 예정인지 미리 보여줌
 * - 감지된 의도
 * - 예정 작업 리스트
 */
export function ExecutionPlanPage({ plan }: ExecutionPlanPageProps) {
  const { intent, confidence, execution_steps, keywords, isLoading } = plan

  // ✅ 로딩 상태 UI
  if (isLoading) {
    return (
      <div className="flex justify-start mb-4">
        <div className="flex items-start gap-3 max-w-2xl w-full">
          <Card className="p-4 bg-card border flex-1">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <div>
                <h3 className="text-lg font-semibold">작업 계획 분석 중...</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  질문을 분석하고 실행 계획을 수립하고 있습니다
                </p>
              </div>
            </div>

            {/* 스켈레톤 로딩 */}
            <div className="mt-4 space-y-3">
              <div className="h-20 bg-muted/50 animate-pulse rounded-lg"></div>
              <div className="space-y-2">
                <div className="h-12 bg-muted/30 animate-pulse rounded-md"></div>
                <div className="h-12 bg-muted/30 animate-pulse rounded-md"></div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  // 의도 타입에 따른 한글 이름 매핑
  const intentNameMap: Record<string, string> = {
    legal_consult: "법률 상담",
    market_inquiry: "시세 조회",
    loan_consult: "대출 상담",
    contract_creation: "계약서 작성",
    contract_review: "계약서 검토",
    comprehensive: "종합 분석",
    risk_analysis: "리스크 분석",
    unclear: "명확화 필요",
    irrelevant: "기능 외 질문"
  }

  const intentName = intentNameMap[intent] || intent

  // 팀 이름 매핑
  const teamNameMap: Record<string, string> = {
    search: "검색",
    analysis: "분석",
    document: "문서",
    search_team: "검색팀",
    analysis_team: "분석팀",
    document_team: "문서팀"
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-4 bg-card border flex-1">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                작업 계획이 수립되었습니다
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                다음 작업들을 순차적으로 수행합니다
              </p>
            </div>
          </div>

          {/* 의도 정보 */}
          <div className="bg-muted/50 rounded-lg p-3 mb-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">감지된 의도:</span>
                <Badge variant="secondary">{intentName}</Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                신뢰도: {(confidence * 100).toFixed(0)}%
              </div>
            </div>

            {keywords && keywords.length > 0 && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-muted-foreground">키워드:</span>
                <div className="flex gap-1 flex-wrap">
                  {keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 예정 작업 리스트 */}
          <div className="space-y-2">
            <div className="text-sm font-medium mb-2">예정 작업:</div>
            {execution_steps.map((step, index) => (
              <div
                key={step.step_id}
                className="flex items-start gap-3 p-2 rounded-md bg-muted/30"
              >
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                  {index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{step.task || step.description}</span>
                    <Badge variant="outline" className="text-xs">
                      {teamNameMap[step.team] || step.team}
                    </Badge>
                  </div>
                  {step.task && step.task !== step.description && (
                    <div className="text-xs text-muted-foreground mt-1">
                      {step.description}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
