"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Shield, AlertTriangle, CheckCircle, XCircle, TrendingUp } from "lucide-react"

interface VerificationResult {
  propertyId: string
  address: string
  trustScore: number
  riskLevel: "low" | "medium" | "high"
  fraudRisk: number
  priceAccuracy: number
  ownerCredibility: number
  issues: Array<{
    type: "fraud" | "price" | "owner" | "document"
    severity: "low" | "medium" | "high"
    title: string
    description: string
  }>
}

export function VerificationAgent() {
  const [activeTab, setActiveTab] = useState("fraud-detection")
  const [propertyUrl, setPropertyUrl] = useState("")
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null)

  const handleVerification = async () => {
    if (!propertyUrl.trim()) return

    setIsVerifying(true)

    // Mock verification process
    setTimeout(() => {
      setVerificationResult({
        propertyId: "PROP-2024-001",
        address: "서울특별시 강남구 역삼동 123-45",
        trustScore: 72,
        riskLevel: "medium",
        fraudRisk: 25,
        priceAccuracy: 85,
        ownerCredibility: 78,
        issues: [
          {
            type: "fraud",
            severity: "medium",
            title: "매물 정보 불일치",
            description: "등기부등본상 면적과 광고 면적이 다릅니다.",
          },
          {
            type: "price",
            severity: "low",
            title: "시세 대비 높은 가격",
            description: "주변 시세보다 15% 높은 가격으로 책정되어 있습니다.",
          },
          {
            type: "owner",
            severity: "high",
            title: "임대인 신용도 주의",
            description: "임대인의 금융 신용도가 평균 이하입니다.",
          },
        ],
      })
      setIsVerifying(false)
    }, 3000)
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case "low":
        return "text-green-600 bg-green-50"
      case "medium":
        return "text-yellow-600 bg-yellow-50"
      case "high":
        return "text-red-600 bg-red-50"
      default:
        return "text-gray-600 bg-gray-50"
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "high":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "medium":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case "low":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h2 className="text-xl font-semibold text-foreground">검증 에이전트</h2>
        <p className="text-sm text-muted-foreground">허위매물 탐지 및 전세사기 위험도를 평가합니다</p>
      </div>

      {/* Content */}
      <div className="flex-1 p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="fraud-detection">허위매물 탐지</TabsTrigger>
            <TabsTrigger value="fraud-risk">전세사기 위험도</TabsTrigger>
            <TabsTrigger value="owner-check">임대인 신용도</TabsTrigger>
          </TabsList>

          <TabsContent value="fraud-detection" className="mt-4 space-y-6">
            {/* Input Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  매물 검증
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="property-url">매물 URL 또는 매물 정보</Label>
                  <Input
                    id="property-url"
                    placeholder="매물 URL을 입력하거나 매물 정보를 입력하세요"
                    value={propertyUrl}
                    onChange={(e) => setPropertyUrl(e.target.value)}
                  />
                </div>
                <Button onClick={handleVerification} disabled={!propertyUrl.trim() || isVerifying} className="w-full">
                  {isVerifying ? "검증 중..." : "매물 검증 시작"}
                </Button>
              </CardContent>
            </Card>

            {/* Verification Progress */}
            {isVerifying && (
              <Card>
                <CardContent className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                      <span className="text-sm">AI가 매물을 검증하고 있습니다...</span>
                    </div>
                    <Progress value={75} className="w-full" />
                    <div className="text-xs text-muted-foreground">공적 데이터와 교차 검증 중...</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Verification Results */}
            {verificationResult && (
              <div className="space-y-4">
                {/* Trust Score */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>신뢰도 점수</span>
                      <Badge className={getRiskColor(verificationResult.riskLevel)}>
                        {verificationResult.riskLevel === "low" && "낮은 위험"}
                        {verificationResult.riskLevel === "medium" && "보통 위험"}
                        {verificationResult.riskLevel === "high" && "높은 위험"}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-primary mb-2">{verificationResult.trustScore}/100</div>
                        <Progress value={verificationResult.trustScore} className="w-full" />
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <div className="text-sm text-muted-foreground">허위매물 위험</div>
                          <div className="text-lg font-semibold text-red-600">{verificationResult.fraudRisk}%</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">가격 정확도</div>
                          <div className="text-lg font-semibold text-green-600">
                            {verificationResult.priceAccuracy}%
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">임대인 신용도</div>
                          <div className="text-lg font-semibold text-yellow-600">
                            {verificationResult.ownerCredibility}%
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Issues Found */}
                <Card>
                  <CardHeader>
                    <CardTitle>발견된 위험요소</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {verificationResult.issues.map((issue, index) => (
                        <div key={index} className="flex items-start gap-3 p-3 border border-border rounded-lg">
                          {getSeverityIcon(issue.severity)}
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium text-sm">{issue.title}</h4>
                              <Badge variant="outline" className="text-xs">
                                {issue.type === "fraud" && "허위매물"}
                                {issue.type === "price" && "가격"}
                                {issue.type === "owner" && "임대인"}
                                {issue.type === "document" && "서류"}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">{issue.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Recommendations */}
                <Card>
                  <CardHeader>
                    <CardTitle>권장사항</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <p>• 등기부등본을 직접 확인하여 매물 정보를 검증하세요</p>
                      <p>• 주변 시세를 추가로 조사해보세요</p>
                      <p>• 임대인의 신용도를 별도로 확인하는 것을 권장합니다</p>
                      <p>• 계약 전 전문가 상담을 받아보세요</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="fraud-risk" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  전세사기 위험도 평가
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-muted-foreground">매물 검증을 먼저 진행해주세요.</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="owner-check" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  임대인 신용도 체크
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-muted-foreground">매물 검증을 먼저 진행해주세요.</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
