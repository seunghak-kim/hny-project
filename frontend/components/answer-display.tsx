"use client"

import React from "react"
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { ProgressBar } from "@/components/ui/progress-bar"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  Scale,
  Info,
  Target,
  BarChart3,
  MessageSquare
} from "lucide-react"
import { cn } from "@/lib/utils"

interface AnswerSection {
  title: string
  content: string | string[]
  icon?: string
  priority?: "high" | "medium" | "low"
  expandable?: boolean
  type?: "text" | "checklist" | "warning"
}

interface AnswerMetadata {
  confidence: number
  sources: string[]
  intent_type: string
}

interface AnswerDisplayProps {
  sections: AnswerSection[]
  metadata: AnswerMetadata
}

export function AnswerDisplay({ sections, metadata }: AnswerDisplayProps) {
  // 아이콘 매핑
  const getIcon = (iconName?: string) => {
    const icons: Record<string, JSX.Element> = {
      "target": <Target className="w-4 h-4 text-primary" />,
      "scale": <Scale className="w-4 h-4 text-blue-500" />,
      "lightbulb": <Lightbulb className="w-4 h-4 text-yellow-500" />,
      "alert": <AlertCircle className="w-4 h-4 text-orange-500" />,
      "info": <Info className="w-4 h-4 text-gray-500" />,
      "chart": <BarChart3 className="w-4 h-4 text-purple-500" />,
      "message": <MessageSquare className="w-4 h-4 text-primary" />
    }
    return icons[iconName || ""] || null
  }

  // 콘텐츠 렌더링
  const renderContent = (section: AnswerSection) => {
    // 체크리스트 타입
    if (section.type === "checklist" && Array.isArray(section.content)) {
      return (
        <ul className="space-y-2 mt-2">
          {section.content.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm">{item}</span>
            </li>
          ))}
        </ul>
      )
    }

    // 경고 타입
    if (section.type === "warning") {
      return (
        <Alert className="mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{section.content}</AlertDescription>
        </Alert>
      )
    }

    // 기본 텍스트
    const contentText = Array.isArray(section.content)
      ? section.content.join("\n")
      : section.content

    return (
      <div className="text-sm mt-2 whitespace-pre-wrap">
        {contentText}
      </div>
    )
  }

  // 의도 타입 한글 변환
  const getIntentLabel = (intent: string) => {
    const labels: Record<string, string> = {
      "legal_consult": "법률 상담",
      "market_inquiry": "시세 조회",
      "loan_consult": "대출 상담",
      "contract_review": "계약서 검토",
      "contract_creation": "계약서 작성",
      "comprehensive": "종합 분석",
      "risk_analysis": "리스크 분석",
      "unclear": "명확화 필요",
      "irrelevant": "기능 외 질문",
      "unknown": "분석 중"
    }
    return labels[intent] || intent
  }

  // 신뢰도에 따른 색상
  const getConfidenceVariant = (confidence: number) => {
    if (confidence >= 0.8) return "success"
    if (confidence >= 0.6) return "warning"
    return "error"
  }

  return (
    <Card className="max-w-3xl">
      {/* 헤더: 메타데이터 */}
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {getIntentLabel(metadata.intent_type)}
            </Badge>
            {metadata.confidence >= 0.8 && (
              <Badge variant="default" className="bg-green-500 text-xs">
                검증됨
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              신뢰도
            </span>
            <ProgressBar
              value={metadata.confidence * 100}
              size="sm"
              variant={getConfidenceVariant(metadata.confidence)}
              className="w-20"
            />
            <span className="text-xs text-muted-foreground">
              {(metadata.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </CardHeader>

      {/* 본문: 섹션별 내용 */}
      <CardContent className="pt-0">
        {sections.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            응답을 생성할 수 없습니다.
          </div>
        ) : (
          <div className="space-y-3">
            {sections.map((section, idx) => {
              const isHighPriority = section.priority === "high"
              const isExpandable = section.expandable !== false

              // 핵심 답변은 아코디언 없이 바로 표시
              if (!section.expandable) {
                return (
                  <div key={idx} className="pb-3 border-b last:border-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getIcon(section.icon)}
                      <h3 className={cn(
                        "text-sm",
                        isHighPriority && "font-semibold"
                      )}>
                        {section.title}
                      </h3>
                    </div>
                    {renderContent(section)}
                  </div>
                )
              }

              // 나머지는 아코디언으로
              return (
                <Accordion
                  key={idx}
                  type="single"
                  collapsible
                  defaultValue={isHighPriority ? "item" : undefined}
                >
                  <AccordionItem value="item" className="border-b-0">
                    <AccordionTrigger className="hover:no-underline py-2">
                      <div className="flex items-center gap-2">
                        {getIcon(section.icon)}
                        <span className={cn(
                          "text-sm",
                          isHighPriority && "font-semibold"
                        )}>
                          {section.title}
                        </span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="pb-2">
                      {renderContent(section)}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              )
            })}
          </div>
        )}
      </CardContent>

      {/* 푸터: 출처 */}
      {metadata.sources && metadata.sources.length > 0 && (
        <CardFooter className="pt-3 border-t">
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">참고 자료: </span>
            {metadata.sources.join(" · ")}
          </div>
        </CardFooter>
      )}
    </Card>
  )
}