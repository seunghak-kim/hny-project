"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Upload, FileText, AlertTriangle, CheckCircle, XCircle } from "lucide-react"

interface AnalysisResult {
  riskLevel: "low" | "medium" | "high"
  score: number
  issues: Array<{
    type: "warning" | "error" | "info"
    title: string
    description: string
  }>
  summary: string
}

export function ContractAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [contractText, setContractText] = useState("")

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Mock file processing
      setContractText("임대차계약서 내용이 업로드되었습니다...")
    }
  }

  const handleAnalyze = async () => {
    if (!contractText.trim()) return

    setIsAnalyzing(true)

    // Mock analysis
    setTimeout(() => {
      setAnalysisResult({
        riskLevel: "medium",
        score: 75,
        issues: [
          {
            type: "warning",
            title: "보증금 반환 조건 불명확",
            description: "보증금 반환 시기와 조건이 명확하게 명시되지 않았습니다.",
          },
          {
            type: "error",
            title: "특약사항 누락",
            description: "수리 및 관리비 부담 주체가 명시되지 않았습니다.",
          },
          {
            type: "info",
            title: "계약 기간 적정",
            description: "계약 기간이 일반적인 범위 내에 있습니다.",
          },
        ],
        summary: "전반적으로 표준적인 계약서이나, 일부 조항에서 개선이 필요합니다.",
      })
      setIsAnalyzing(false)
    }, 3000)
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case "low":
        return "text-green-600"
      case "medium":
        return "text-yellow-600"
      case "high":
        return "text-red-600"
      default:
        return "text-gray-600"
    }
  }

  const getIssueIcon = (type: string) => {
    switch (type) {
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case "info":
        return <CheckCircle className="h-4 w-4 text-blue-500" />
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            계약서 업로드
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-2">계약서 파일을 드래그하거나 클릭하여 업로드하세요</p>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.png"
              onChange={handleFileUpload}
              className="hidden"
              id="contract-upload"
            />
            <Label htmlFor="contract-upload">
              <Button variant="outline" className="cursor-pointer bg-transparent">
                파일 선택
              </Button>
            </Label>
          </div>

          <div className="space-y-2">
            <Label htmlFor="contract-text">또는 계약서 내용을 직접 입력하세요</Label>
            <Textarea
              id="contract-text"
              placeholder="계약서 주요 내용을 입력해주세요..."
              value={contractText}
              onChange={(e) => setContractText(e.target.value)}
              rows={6}
            />
          </div>

          <Button onClick={handleAnalyze} disabled={!contractText.trim() || isAnalyzing} className="w-full">
            {isAnalyzing ? "분석 중..." : "계약서 분석 시작"}
          </Button>
        </CardContent>
      </Card>

      {/* Analysis Progress */}
      {isAnalyzing && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <span className="text-sm">AI가 계약서를 분석하고 있습니다...</span>
              </div>
              <Progress value={66} className="w-full" />
              <div className="text-xs text-muted-foreground">조항 검토 및 위험요소 탐지 중...</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      {analysisResult && (
        <div className="space-y-4">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>분석 결과</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">위험도:</span>
                  <span className={`font-semibold ${getRiskColor(analysisResult.riskLevel)}`}>
                    {analysisResult.riskLevel === "low" && "낮음"}
                    {analysisResult.riskLevel === "medium" && "보통"}
                    {analysisResult.riskLevel === "high" && "높음"}
                  </span>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">종합 점수</span>
                    <span className="font-semibold">{analysisResult.score}/100</span>
                  </div>
                  <Progress value={analysisResult.score} className="w-full" />
                </div>
                <p className="text-sm text-muted-foreground">{analysisResult.summary}</p>
              </div>
            </CardContent>
          </Card>

          {/* Issues List */}
          <Card>
            <CardHeader>
              <CardTitle>발견된 이슈</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {analysisResult.issues.map((issue, index) => (
                  <div key={index} className="flex items-start gap-3 p-3 border border-border rounded-lg">
                    {getIssueIcon(issue.type)}
                    <div className="flex-1">
                      <h4 className="font-medium text-sm">{issue.title}</h4>
                      <p className="text-sm text-muted-foreground mt-1">{issue.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recommendations */}
          <Card>
            <CardHeader>
              <CardTitle>개선 권장사항</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <p>• 보증금 반환 조건을 명확히 명시하세요</p>
                <p>• 수리 및 관리비 부담 주체를 특약사항에 추가하세요</p>
                <p>• 계약 해지 조건을 구체적으로 작성하세요</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
