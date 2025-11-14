"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  MessageCircleOff,
  HelpCircle,
  AlertCircle,
  CheckCircle2,
  Lightbulb
} from "lucide-react"

interface GuidanceData {
  detected_intent: "irrelevant" | "unclear" | "unknown" | "usage" | "usage_guide"
  original_query: string
  message: string
  features?: any[]
  tips?: string[]
}

interface GuidancePageProps {
  guidance: GuidanceData
}

export function GuidancePage({ guidance }: GuidancePageProps) {
  // Intent별 설정
  const intentConfig = {
    usage_guide: {
      icon: Lightbulb,
      title: "사용법 안내",
      subtitle: "도와줘 홈즈냥즈 활용 가이드",
      badgeVariant: "secondary" as const,
      badgeLabel: "사용법",
      iconColor: "text-green-500"
    },
    usage: {
      icon: Lightbulb,
      title: "사용법 안내",
      subtitle: "도와줘 홈즈냥즈 활용 가이드",
      badgeVariant: "secondary" as const,
      badgeLabel: "사용법",
      iconColor: "text-green-500"
    },
    irrelevant: {
      icon: MessageCircleOff,
      title: "부동산 관련 질문이 아닙니다",
      subtitle: "저는 부동산 전문 상담 AI입니다",
      badgeVariant: "secondary" as const,
      badgeLabel: "기능 외 질문",
      iconColor: "text-orange-500"
    },
    unclear: {
      icon: HelpCircle,
      title: "질문을 명확히 해주세요",
      subtitle: "더 구체적인 정보가 필요합니다",
      badgeVariant: "secondary" as const,
      badgeLabel: "명확화 필요",
      iconColor: "text-blue-500"
    },
    unknown: {
      icon: AlertCircle,
      title: "질문 이해 실패",
      subtitle: "부동산 관련 질문을 명확히 해주세요",
      badgeVariant: "destructive" as const,
      badgeLabel: "분석 실패",
      iconColor: "text-gray-500"
    }
  }

  const config = intentConfig[guidance.detected_intent] || intentConfig.unknown
  const Icon = config.icon

  // 메시지 파싱 - usage_guide의 경우 features 직접 사용
  const sections = guidance.detected_intent === "usage_guide" && guidance.features
    ? { features: guidance.features, tips: guidance.tips }
    : parseMessage(guidance.message, guidance.detected_intent)

  return (
    <div className="flex justify-start">
      <div className="flex gap-2 max-w-[80%]">
        {/* 고양이 아이콘 추가 */}
        <div className="flex-shrink-0 w-24 h-24">
          <img
            src="/images/holmesnyangz.png"
            alt="Holmes Nyangz"
            width={128}
            height={128}
            className="rounded-full object-cover"
          />
        </div>

        <Card className="p-5 bg-card border flex-1">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-3">
              <Icon className={`w-6 h-6 ${config.iconColor} mt-1 flex-shrink-0`} />
              <div>
                <h3 className="text-lg font-semibold">{config.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {config.subtitle}
                </p>
              </div>
            </div>
            <Badge variant={config.badgeVariant} className="ml-2 flex-shrink-0">
              {config.badgeLabel}
            </Badge>
          </div>

          {/* Main Message */}
          {'mainMessage' in sections && sections.mainMessage && (
            <Alert className="mb-4">
              <AlertDescription className="text-sm">
                {sections.mainMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* Usage Guide - Features with Details (3 columns grid) */}
          {guidance.detected_intent === "usage_guide" && guidance.features && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {guidance.features.map((feature: any, idx: number) => (
                  <div key={idx} className="border rounded-lg p-4 bg-blue-50/50 flex flex-col">
                    <div className="flex items-start gap-3 mb-3">
                      <span className="text-2xl">{feature.icon}</span>
                      <div className="flex-1">
                        <h4 className="font-semibold text-base mb-1">{feature.title}</h4>
                        <p className="text-sm text-muted-foreground mb-2">{feature.description}</p>
                      </div>
                    </div>
                    <ul className="space-y-1 mb-3 flex-1">
                      {feature.items?.map((item: string, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                    {feature.examples && feature.examples.length > 0 && (
                      <div className="bg-white/80 rounded p-2 mt-auto">
                        <p className="text-xs font-semibold text-blue-700 mb-1">💡 예시:</p>
                        {feature.examples.map((example: string, i: number) => (
                          <div key={i} className="text-xs text-blue-600 ml-2">
                            • "{example}"
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Usage Tips */}
              {guidance.tips && guidance.tips.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mt-4">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-5 h-5 text-amber-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-sm text-amber-900 mb-2">💡 사용 팁</h4>
                      <ul className="space-y-1">
                        {guidance.tips.map((tip: string, i: number) => (
                          <li key={i} className="text-sm text-amber-800">• {tip}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Features (irrelevant and usage) */}
          {(guidance.detected_intent === "irrelevant" || guidance.detected_intent === "usage") && 'features' in sections && sections.features && sections.features.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <h4 className="text-sm font-semibold">
                  {guidance.detected_intent === "usage" ? "주요 기능" : "제가 도와드릴 수 있는 분야"}
                </h4>
              </div>
              <ul className="space-y-2 ml-6">
                {sections.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">•</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tips (unclear only) */}
          {guidance.detected_intent === "unclear" && 'tips' in sections && sections.tips && sections.tips.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4 text-yellow-500" />
                <h4 className="text-sm font-semibold">더 구체적으로 질문해주시면 도움이 됩니다</h4>
              </div>
              <ul className="space-y-2 ml-6">
                {sections.tips.map((tip, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Example Questions */}
          {'examples' in sections && sections.examples && sections.examples.length > 0 && (
            <div className="mt-4 p-3 bg-muted/50 rounded-lg">
              <h4 className="text-sm font-semibold mb-2">예시 질문:</h4>
              <div className="space-y-2">
                {sections.examples.map((example, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-muted-foreground">{idx + 1}.</span>
                    <span className="text-primary font-medium">"{example}"</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Original Query */}
          {guidance.original_query && (
            <div className="mt-4 pt-3 border-t text-xs text-muted-foreground">
              질문: "{guidance.original_query}"
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

// Helper: 메시지 파싱
function parseMessage(message: string, intent: string) {
  const sections: {
    mainMessage?: string
    features?: string[]
    tips?: string[]
    examples?: string[]
  } = {}

  // 첫 번째 단락을 Main Message로 추출
  const lines = message.split('\n').filter(line => line.trim())
  if (lines.length > 0) {
    // 첫 2-3줄을 메인 메시지로
    sections.mainMessage = lines.slice(0, 3).join(' ').replace(/\*\*/g, '')
  }

  if (intent === "irrelevant") {
    // "제가 도와드릴 수 있는 분야:" 섹션 추출
    const featuresMatch = message.match(/\*\*제가 도와드릴 수 있는 분야:\*\*\n((?:- .+\n?)+)/)
    if (featuresMatch) {
      sections.features = featuresMatch[1]
        .split('\n')
        .filter(line => line.trim().startsWith('-'))
        .map(line => line.replace(/^-\s*/, '').trim())
    }
  }

  if (intent === "usage") {
    // "제가 도와드릴 수 있는 주요 기능:" 섹션에서 각 기능의 세부 항목 추출
    const features: string[] = []

    // 📋, 🏠, 💰, 📝, 🔍 등의 이모지로 시작하는 섹션 찾기
    const sectionRegex = /[📋🏠💰📝🔍]\s+\*\*\d+\.\s+(.+?)\*\*\n((?:- .+\n?)+)/g
    let match

    while ((match = sectionRegex.exec(message)) !== null) {
      const sectionTitle = match[1]
      const items = match[2]
        .split('\n')
        .filter(line => line.trim().startsWith('-'))
        .map(line => line.replace(/^-\s*/, '').trim())

      features.push(`**${sectionTitle}**`)
      features.push(...items.map(item => `  • ${item}`))
    }

    if (features.length > 0) {
      sections.features = features
    }
  }

  if (intent === "unclear") {
    // "더 구체적으로 질문해주시면..." 섹션 추출
    const tipsMatch = message.match(/\*\*더 구체적으로 질문해주시면 도움이 됩니다:\*\*\n((?:- .+\n?)+)/)
    if (tipsMatch) {
      sections.tips = tipsMatch[1]
        .split('\n')
        .filter(line => line.trim().startsWith('-'))
        .map(line => line.replace(/^-\s*/, '').trim())
    }

    // "예시:" 섹션 추출
    const examplesMatch = message.match(/\*\*예시:\*\*\n((?:- .+\n?)+)/)
    if (examplesMatch) {
      sections.examples = examplesMatch[1]
        .split('\n')
        .filter(line => line.trim().startsWith('-'))
        .map(line => line.replace(/^-\s*/, '').replace(/"/g, '').trim())
    }
  }

  return sections
}
