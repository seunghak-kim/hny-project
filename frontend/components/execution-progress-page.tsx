"use client"

import { Card } from "@/components/ui/card"
import { ProgressBar } from "@/components/ui/progress-bar"
import { StepItem } from "@/components/step-item"
import type { ExecutionStep, ExecutionPlan } from "@/types/execution"

interface ExecutionProgressPageProps {
  steps: ExecutionStep[]
  plan: ExecutionPlan        // ExecutionPlan 전체
}

/**
 * 작업 실행 중 페이지 (TODO 스타일)
 *
 * execution_steps 기반 실시간 진행 상황 표시
 * - 개별 작업 진행 상황 (StepItem)
 * - 전체 진행률
 */
export function ExecutionProgressPage({
  steps,
  plan
}: ExecutionProgressPageProps) {
  // 진행 상황 계산
  const totalSteps = steps.length
  const completedSteps = steps.filter(s => s.status === "completed").length
  const failedSteps = steps.filter(s => s.status === "failed").length
  const currentStep = steps.find(s => s.status === "in_progress")

  // 전체 진행률 (0-100)
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-5xl w-full">
        <Card className="p-0 bg-card border flex-1 overflow-hidden">
          {/* 상단: 제목과 설명 */}
          <div className="px-6 pt-6 pb-3">
            <h3 className="text-2xl font-bold">
              작업 실행 중
              <span className="text-base font-normal text-muted-foreground ml-2">
                ({completedSteps}/{totalSteps} 완료)
              </span>
            </h3>
            {currentStep && (
              <p className="text-sm text-muted-foreground mt-1">
                현재: {currentStep.description}
              </p>
            )}
          </div>

          {/* 하단: GIF와 콘텐츠 - 30:70 비율 */}
          <div className="flex items-start gap-4 px-6 pb-6">
            {/* 좌측 스피너 - 30% */}
            <div className="w-[30%] flex-shrink-0">
              <img
                src="/animation/spinner/2_execution-progress_spinner.gif"
                alt="executing"
                className="w-full h-auto object-contain"
              />
            </div>

            {/* 우측 콘텐츠 - 70% */}
            <div className="w-[70%] flex-shrink-0">

              {/* 전체 진행률 */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">전체 진행률</span>
                  <span className="text-sm text-muted-foreground">
                    {overallProgress.toFixed(0)}%
                  </span>
                </div>
                <ProgressBar
                  value={overallProgress}
                  size="md"
                  variant={failedSteps > 0 ? "warning" : "default"}
                />
              </div>

              {/* 작업 리스트 */}
              <div className="space-y-2">
                <div className="text-sm font-medium mb-2">진행 상황:</div>
                {steps.map((step, index) => (
                  <StepItem
                    key={step.step_id}
                    step={step}
                    index={index}
                  />
                ))}
              </div>

              {/* 실패한 작업이 있을 경우 */}
              {failedSteps > 0 && (
                <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-xs text-red-700 dark:text-red-400">
                    ⚠️ {failedSteps}개의 작업이 실패했습니다. 일부 정보가 누락될 수 있습니다.
                  </p>
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
