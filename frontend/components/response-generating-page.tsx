"use client"

import React from "react"
import { Card } from "@/components/ui/card"

interface ResponseGeneratingPageProps {
  message?: string
  phase?: "aggregation" | "response_generation"
}

export function ResponseGeneratingPage({
  message = "답변을 생성하고 있습니다...",
  phase = "response_generation"
}: ResponseGeneratingPageProps) {
  const steps = [
    {
      id: "collect",
      label: "데이터 수집 완료",
      status: "completed" as const
    },
    {
      id: "organize",
      label: "정보 정리 중",
      status: phase === "aggregation" ? ("in_progress" as const) : ("completed" as const)
    },
    {
      id: "generate",
      label: "최종 답변 생성 중",
      status: phase === "response_generation" ? ("in_progress" as const) : ("pending" as const)
    }
  ]

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-5xl w-full">
        <Card className="p-0 bg-card border flex-1 overflow-hidden">
          {/* 상단: 제목과 설명 */}
          <div className="px-6 pt-6 pb-3">
            <h3 className="text-2xl font-bold text-foreground">AI 응답 생성 중</h3>
            <p className="text-sm text-muted-foreground mt-1">{message}</p>
          </div>

          {/* 하단: GIF와 콘텐츠 - 30:70 비율 */}
          <div className="flex items-start gap-4 px-6 pb-6">
            {/* 좌측 스피너 - 30% */}
            <div className="w-[30%] flex-shrink-0">
              <img
                src="/animation/spinner/3response-generating_spinner.gif"
                alt="generating response"
                className="w-full h-auto object-contain"
              />
            </div>

            {/* 우측 콘텐츠 - 70% */}
            <div className="w-[70%] flex-shrink-0">

              {/* 진행 단계 표시 */}
              <div className="space-y-3">
                {steps.map((step, index) => (
                  <div key={step.id} className="flex items-center gap-3">
                    {/* 상태 아이콘 */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                      step.status === "completed"
                        ? "bg-primary border-primary text-primary-foreground"
                        : step.status === "in_progress"
                        ? "bg-primary/20 border-primary text-primary animate-pulse"
                        : "bg-muted border-muted-foreground/20 text-muted-foreground"
                    }`}>
                      {step.status === "completed" ? (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : step.status === "in_progress" ? (
                        <div className="w-3 h-3 bg-primary rounded-full animate-ping" />
                      ) : (
                        <div className="w-3 h-3 bg-muted-foreground/20 rounded-full" />
                      )}
                    </div>

                    {/* 단계 레이블 */}
                    <div className="flex-1">
                      <p className={`text-sm font-medium transition-colors ${
                        step.status === "completed" || step.status === "in_progress"
                          ? "text-foreground"
                          : "text-muted-foreground"
                      }`}>
                        {step.label}
                      </p>
                    </div>

                    {/* 연결선 (마지막 항목 제외) */}
                    {index < steps.length - 1 && (
                      <div className="absolute left-[19px] w-0.5 h-6 bg-border" style={{ marginTop: "2rem" }} />
                    )}
                  </div>
                ))}
              </div>

              {/* 추가 정보 */}
              <div className="pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground text-center">
                  잠시만 기다려주세요. 최적의 답변을 준비하고 있습니다.
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
