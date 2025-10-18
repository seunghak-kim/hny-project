"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Users, Home, FileText, HelpCircle, MapPin } from "lucide-react"

interface PropertyRecommendation {
  id: string
  name: string
  address: string
  price: string
  type: string
  area: string
  year: number
  features: string[]
  matchScore: number
}

interface GovernmentPolicy {
  id: string
  title: string
  description: string
  eligibility: string[]
  benefits: string
  deadline?: string
}

export function ConsultationAgent() {
  const [activeTab, setActiveTab] = useState("recommendations")
  const [preferences, setPreferences] = useState({
    location: "",
    budget: "",
    propertyType: "",
    features: [] as string[],
  })

  const mockRecommendations: PropertyRecommendation[] = [
    {
      id: "1",
      name: "강남 센트럴 아파트",
      address: "서울특별시 강남구 역삼동",
      price: "12억 원",
      type: "아파트",
      area: "84㎡",
      year: 2020,
      features: ["지하철 인근", "학군 우수", "신축"],
      matchScore: 95,
    },
    {
      id: "2",
      name: "서초 그린빌라",
      address: "서울특별시 서초구 서초동",
      price: "8억 원",
      type: "빌라",
      area: "76㎡",
      year: 2018,
      features: ["조용한 주거지", "주차 편리"],
      matchScore: 87,
    },
  ]

  const mockPolicies: GovernmentPolicy[] = [
    {
      id: "1",
      title: "생애최초 주택구입 지원",
      description: "생애 최초로 주택을 구입하는 무주택자를 위한 정부 지원 정책",
      eligibility: ["무주택자", "연소득 7천만원 이하", "생애최초 구입"],
      benefits: "최대 3억원 대출, 금리 우대",
      deadline: "2024년 12월 31일",
    },
    {
      id: "2",
      title: "신혼부부 전세자금 대출",
      description: "신혼부부의 주거 안정을 위한 전세자금 대출 지원",
      eligibility: ["혼인 7년 이내", "합산소득 7천만원 이하"],
      benefits: "최대 2억원 대출, 연 1.8% 금리",
    },
  ]

  const handleFeatureChange = (feature: string, checked: boolean) => {
    setPreferences((prev) => ({
      ...prev,
      features: checked ? [...prev.features, feature] : prev.features.filter((f) => f !== feature),
    }))
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h2 className="text-xl font-semibold text-foreground">상담 에이전트</h2>
        <p className="text-sm text-muted-foreground">맞춤형 매물 추천 및 부동산 상담을 제공합니다</p>
      </div>

      {/* Content */}
      <div className="flex-1 p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="recommendations">매물 추천</TabsTrigger>
            <TabsTrigger value="policies">정부 정책</TabsTrigger>
            <TabsTrigger value="process">거래 절차</TabsTrigger>
            <TabsTrigger value="qna">Q&A</TabsTrigger>
          </TabsList>

          <TabsContent value="recommendations" className="mt-4 space-y-6">
            {/* Preference Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Home className="h-5 w-5" />
                  선호 조건 설정
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>희망 지역</Label>
                    <Select
                      value={preferences.location}
                      onValueChange={(value) => setPreferences((prev) => ({ ...prev, location: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="지역을 선택하세요" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gangnam">강남구</SelectItem>
                        <SelectItem value="seocho">서초구</SelectItem>
                        <SelectItem value="songpa">송파구</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>예산 범위</Label>
                    <Select
                      value={preferences.budget}
                      onValueChange={(value) => setPreferences((prev) => ({ ...prev, budget: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="예산을 선택하세요" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="under-5">5억 이하</SelectItem>
                        <SelectItem value="5-10">5억 ~ 10억</SelectItem>
                        <SelectItem value="10-15">10억 ~ 15억</SelectItem>
                        <SelectItem value="over-15">15억 이상</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>매물 유형</Label>
                    <Select
                      value={preferences.propertyType}
                      onValueChange={(value) => setPreferences((prev) => ({ ...prev, propertyType: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="유형을 선택하세요" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="apartment">아파트</SelectItem>
                        <SelectItem value="villa">빌라</SelectItem>
                        <SelectItem value="officetel">오피스텔</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>선호 조건 (복수 선택 가능)</Label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {["지하철 인근", "학군 우수", "신축", "주차 편리", "조용한 주거지", "상가 인근"].map((feature) => (
                      <div key={feature} className="flex items-center space-x-2">
                        <Checkbox
                          id={feature}
                          checked={preferences.features.includes(feature)}
                          onCheckedChange={(checked) => handleFeatureChange(feature, checked as boolean)}
                        />
                        <Label htmlFor={feature} className="text-sm">
                          {feature}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <Button className="w-full">맞춤 매물 찾기</Button>
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle>추천 매물</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockRecommendations.map((property) => (
                    <div key={property.id} className="border border-border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-semibold">{property.name}</h3>
                          <p className="text-sm text-muted-foreground flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {property.address}
                          </p>
                        </div>
                        <Badge variant="secondary" className="bg-green-100 text-green-800">
                          매칭도 {property.matchScore}%
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                        <div>
                          <span className="text-sm text-muted-foreground">가격</span>
                          <p className="font-medium">{property.price}</p>
                        </div>
                        <div>
                          <span className="text-sm text-muted-foreground">유형</span>
                          <p className="font-medium">{property.type}</p>
                        </div>
                        <div>
                          <span className="text-sm text-muted-foreground">면적</span>
                          <p className="font-medium">{property.area}</p>
                        </div>
                        <div>
                          <span className="text-sm text-muted-foreground">준공년도</span>
                          <p className="font-medium">{property.year}년</p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-1 mb-3">
                        {property.features.map((feature, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {feature}
                          </Badge>
                        ))}
                      </div>

                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          상세 보기
                        </Button>
                        <Button size="sm">문의하기</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="policies" className="mt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  정부 지원 정책
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockPolicies.map((policy) => (
                    <div key={policy.id} className="border border-border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold">{policy.title}</h3>
                        {policy.deadline && (
                          <Badge variant="destructive" className="text-xs">
                            마감: {policy.deadline}
                          </Badge>
                        )}
                      </div>

                      <p className="text-sm text-muted-foreground mb-3">{policy.description}</p>

                      <div className="space-y-2 mb-3">
                        <div>
                          <span className="text-sm font-medium">지원 대상:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {policy.eligibility.map((item, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {item}
                              </Badge>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="text-sm font-medium">지원 내용:</span>
                          <p className="text-sm text-muted-foreground">{policy.benefits}</p>
                        </div>
                      </div>

                      <Button size="sm" variant="outline">
                        자세히 보기
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="process" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  부동산 거래 절차 가이드
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="border-l-4 border-primary pl-4">
                    <h3 className="font-semibold mb-2">1. 매물 탐색 및 선정</h3>
                    <p className="text-sm text-muted-foreground">
                      • 예산 및 조건 설정
                      <br />• 매물 정보 수집 및 비교
                      <br />• 현장 방문 및 확인
                    </p>
                  </div>

                  <div className="border-l-4 border-primary pl-4">
                    <h3 className="font-semibold mb-2">2. 서류 확인 및 검증</h3>
                    <p className="text-sm text-muted-foreground">
                      • 등기부등본 확인
                      <br />• 건축물대장 검토
                      <br />• 임대인 신분 확인
                    </p>
                  </div>

                  <div className="border-l-4 border-primary pl-4">
                    <h3 className="font-semibold mb-2">3. 계약 체결</h3>
                    <p className="text-sm text-muted-foreground">
                      • 계약서 작성 및 검토
                      <br />• 특약사항 협의
                      <br />• 계약금 지급
                    </p>
                  </div>

                  <div className="border-l-4 border-primary pl-4">
                    <h3 className="font-semibold mb-2">4. 잔금 지급 및 입주</h3>
                    <p className="text-sm text-muted-foreground">
                      • 잔금 지급
                      <br />• 열쇠 인수
                      <br />• 전입신고 및 주소 변경
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="qna" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HelpCircle className="h-5 w-5" />
                  자주 묻는 질문
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="border border-border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">전세사기를 어떻게 예방할 수 있나요?</h3>
                    <p className="text-sm text-muted-foreground">
                      등기부등본을 통해 소유자 확인, 선순위 근저당권 확인, 임대인 신분증 확인 등을 통해 예방할 수
                      있습니다.
                    </p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">계약서에서 꼭 확인해야 할 사항은?</h3>
                    <p className="text-sm text-muted-foreground">
                      임대차 기간, 보증금 반환 조건, 수리 및 관리비 부담 주체, 특약사항 등을 꼼꼼히 확인해야 합니다.
                    </p>
                  </div>

                  <div className="border border-border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">중개수수료는 얼마인가요?</h3>
                    <p className="text-sm text-muted-foreground">
                      매매의 경우 거래금액의 0.5% 이내, 임대차의 경우 보증금의 0.5% 이내에서 중개수수료를 받을 수
                      있습니다.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
