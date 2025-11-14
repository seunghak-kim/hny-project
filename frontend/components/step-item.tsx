"use client"

import { CheckCircle2, XCircle, Loader2, Clock, SkipForward, Ban } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { ProgressBar } from "@/components/ui/progress-bar"
import type { ExecutionStep } from "@/types/execution"
import { cn } from "@/lib/utils"

interface StepItemProps {
  step: ExecutionStep
  index: number
  isExpanded?: boolean
}

/**
 * 개별 작업 아이템 컴포넌트 (TODO 스타일)
 *
 * 상태별 표시:
 * - pending: ⏸ 대기 중
 * - in_progress: ⏳ 진행 중 (진행률 바)
 * - completed: ✅ 완료
 * - failed: ❌ 실패
 * - skipped: ⏭ 건너뜀
 * - cancelled: 🚫 취소됨
 */
export function StepItem({ step, index, isExpanded = false }: StepItemProps) {
  const {
    task,
    description,
    team,
    status,
    progress_percentage,
    result,
    error,
    started_at,
    completed_at
  } = step

  // 실행 시간 계산 (started_at, completed_at으로부터)
  const execution_time_ms = started_at && completed_at
    ? new Date(completed_at).getTime() - new Date(started_at).getTime()
    : null

  // 팀 이름 매핑
  const teamNameMap: Record<string, string> = {
    search: "검색",
    analysis: "분석",
    document: "문서",
    search_team: "검색팀",
    analysis_team: "분석팀",
    document_team: "문서팀"
  }

  // 상태별 아이콘 및 색상
  const statusConfig = {
    pending: {
      icon: Clock,
      color: "text-muted-foreground",
      bgColor: "bg-muted",
      label: "대기 중"
    },
    in_progress: {
      icon: Loader2,
      color: "text-primary",
      bgColor: "bg-primary/10",
      label: "진행 중",
      animate: true
    },
    completed: {
      icon: CheckCircle2,
      color: "text-green-600",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      label: "완료"
    },
    failed: {
      icon: XCircle,
      color: "text-red-600",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      label: "실패"
    },
    skipped: {
      icon: SkipForward,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
      label: "건너뜀"
    },
    cancelled: {
      icon: Ban,
      color: "text-gray-600",
      bgColor: "bg-gray-50 dark:bg-gray-900/20",
      label: "취소됨"
    }
  }

  const config = statusConfig[status]
  const Icon = config.icon

  // 실행 시간 포맷팅
  const formatTime = (ms?: number) => {
    if (!ms) return null
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}초`
  }

  // 결과 미리보기 생성
  const getResultPreview = () => {
    if (!result || Object.keys(result).length === 0) return null

    // 결과에서 주요 정보 추출
    const preview: string[] = []

    if (result.legal_info) {
      const legal = result.legal_info
      if (legal.rate_limit) preview.push(`인상률: ${legal.rate_limit}`)
      if (legal.rights) preview.push(`권리: ${legal.rights.join(", ")}`)
    }

    if (result.market_data) {
      const market = result.market_data
      if (market.average_price) preview.push(`평균가: ${market.average_price}`)
    }

    if (result.insights && Array.isArray(result.insights)) {
      preview.push(...result.insights.slice(0, 2))
    }

    return preview.length > 0 ? preview.join(" · ") : null
  }

  const resultPreview = getResultPreview()

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg transition-all",
        config.bgColor,
        status === "in_progress" && "ring-1 ring-primary/20"
      )}
    >
      {/* 번호 + 아이콘 */}
      <div className="flex-shrink-0 flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-background flex items-center justify-center text-xs font-medium">
          {index + 1}
        </div>
        <Icon
          className={cn(
            "w-5 h-5",
            config.color,
            config.animate && "animate-spin"
          )}
        />
      </div>

      {/* 작업 내용 */}
      <div className="flex-1 min-w-0">
        {/* 작업명 + 팀 + 상태 */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn(
            "text-sm font-medium",
            status === "completed" && "line-through text-muted-foreground"
          )}>
            {task || description}
          </span>
          <Badge variant="outline" className="text-xs">
            {teamNameMap[team] || team}
          </Badge>
          {status !== "pending" && (
            <Badge
              variant={status === "completed" ? "default" : "secondary"}
              className="text-xs"
            >
              {config.label}
            </Badge>
          )}
        </div>

        {/* 상세 설명 (task와 description이 다를 경우) */}
        {task && task !== description && (
          <div className="text-xs text-muted-foreground mt-1">
            {description}
          </div>
        )}

        {/* 진행 중: 진행률 바 */}
        {status === "in_progress" && (
          <div className="mt-2">
            <ProgressBar
              value={progress_percentage}
              size="sm"
              showLabel
              className="mb-1"
            />
            <div className="text-xs text-muted-foreground">
              {progress_percentage}% 완료
            </div>
          </div>
        )}

        {/* 완료: 결과 미리보기 */}
        {status === "completed" && resultPreview && (
          <div className="mt-2 text-xs text-muted-foreground">
            └─ {resultPreview}
          </div>
        )}

        {/* 실패: 에러 메시지 */}
        {status === "failed" && error && (
          <div className="mt-2 text-xs text-red-600 dark:text-red-400">
            └─ 오류: {error}
          </div>
        )}

        {/* 실행 시간 */}
        {execution_time_ms && status === "completed" && (
          <div className="mt-1 text-xs text-muted-foreground">
            {formatTime(execution_time_ms)}
          </div>
        )}
      </div>

      {/* 시간 표시 (완료/실패) */}
      {(status === "completed" || status === "failed") && execution_time_ms && (
        <div className="flex-shrink-0 text-xs text-muted-foreground font-mono">
          {formatTime(execution_time_ms)}
        </div>
      )}
    </div>
  )
}
