"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, Building, FileText, MapPin } from "lucide-react"

interface PropertyInfo {
  address: string
  buildingType: string
  totalFloors: number
  buildYear: number
  totalUnits: number
  landArea: string
  buildingArea: string
  ownerInfo: string
  restrictions: string[]
}

export function PropertyDocuments() {
  const [searchType, setSearchType] = useState("address")
  const [searchValue, setSearchValue] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [propertyInfo, setPropertyInfo] = useState<PropertyInfo | null>(null)

  const handleSearch = async () => {
    if (!searchValue.trim()) return

    setIsSearching(true)

    // Mock API call
    setTimeout(() => {
      setPropertyInfo({
        address: "서울특별시 강남구 역삼동 123-45",
        buildingType: "아파트",
        totalFloors: 15,
        buildYear: 2018,
        totalUnits: 200,
        landArea: "1,234.56㎡",
        buildingArea: "12,345.67㎡",
        ownerInfo: "개인 소유",
        restrictions: ["근린생활시설 제한", "용도변경 제한"],
      })
      setIsSearching(false)
    }, 2000)
  }

  return (
    <div className="space-y-6">
      {/* Search Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            부동산 정보 조회
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>검색 유형</Label>
              <Select value={searchType} onValueChange={setSearchType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="address">주소</SelectItem>
                  <SelectItem value="building-number">건물번호</SelectItem>
                  <SelectItem value="lot-number">지번</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label>검색어</Label>
              <div className="flex gap-2">
                <Input
                  placeholder={
                    searchType === "address"
                      ? "예: 서울특별시 강남구 역삼동"
                      : searchType === "building-number"
                        ? "예: 1234-5678"
                        : "예: 123-45"
                  }
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                />
                <Button onClick={handleSearch} disabled={isSearching}>
                  {isSearching ? "검색 중..." : "검색"}
                </Button>
              </div>
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>• 등기부등본 및 건축물대장 정보를 실시간으로 조회합니다</p>
            <p>• 정확한 주소나 지번을 입력해주세요</p>
          </div>
        </CardContent>
      </Card>

      {/* Property Information */}
      {propertyInfo && (
        <div className="space-y-4">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building className="h-5 w-5" />
                건축물 기본정보
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div>
                    <Label className="text-sm text-muted-foreground">주소</Label>
                    <p className="font-medium">{propertyInfo.address}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">건물유형</Label>
                    <p className="font-medium">{propertyInfo.buildingType}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">총 층수</Label>
                    <p className="font-medium">{propertyInfo.totalFloors}층</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">준공년도</Label>
                    <p className="font-medium">{propertyInfo.buildYear}년</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <Label className="text-sm text-muted-foreground">총 세대수</Label>
                    <p className="font-medium">{propertyInfo.totalUnits}세대</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">대지면적</Label>
                    <p className="font-medium">{propertyInfo.landArea}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">건축면적</Label>
                    <p className="font-medium">{propertyInfo.buildingArea}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">소유구분</Label>
                    <p className="font-medium">{propertyInfo.ownerInfo}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Legal Restrictions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                법적 제한사항
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {propertyInfo.restrictions.map((restriction, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 bg-muted rounded">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{restriction}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>추가 조회</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm">
                  등기부등본 전체 조회
                </Button>
                <Button variant="outline" size="sm">
                  건축물대장 상세 조회
                </Button>
                <Button variant="outline" size="sm">
                  토지이용계획 확인
                </Button>
                <Button variant="outline" size="sm">
                  개발제한구역 확인
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
