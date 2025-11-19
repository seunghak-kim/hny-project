"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search } from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { getAllDistrictNames } from "@/lib/district-coordinates"
import { FloatingChatButton } from "@/components/floating-chat-button"
import { useMap } from "./map-interface/use-map"
import { useProperties } from "./map-interface/use-properties"
import { formatPriceInEok } from "./map-interface/price-utils"

export function MapInterface() {
  const mapRef = useRef<HTMLDivElement>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState<string>("전체")
  const [transactionFilter, setTransactionFilter] = useState<string>("매매")
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<string>("전체")
  const [sortBy, setSortBy] = useState<string>("이름순")
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Filter dialogs state
  const [priceFilterOpen, setPriceFilterOpen] = useState(false)
  const [areaFilterOpen, setAreaFilterOpen] = useState(false)

  // Price filter ranges (in 억원)
  const [salePriceRange, setSalePriceRange] = useState<[number, number]>([0, 50])
  const [jeonsePriceRange, setJeonsePriceRange] = useState<[number, number]>([0, 20])
  const [monthlyPriceRange, setMonthlyPriceRange] = useState<[number, number]>([0, 10])

  // Area filter (in 평)
  const [areaRange, setAreaRange] = useState<[number, number]>([0, 70])

  const [sidebarOpen, setSidebarOpen] = useState(true)

  // 서비스 가능 지역 목록
  const serviceAreas = getAllDistrictNames()

  // Use properties hook for data management
  const {
    properties,
    filteredProperties,
    displayedProperties,
    loading,
    isLoadingMore,
    loadPropertiesFromAPI,
    handlePropertyClick,
    handleScroll,
    selectedProperty,
    setSelectedProperty
  } = useProperties({
    map: null, // Will be set by useMap
    propertyTypeFilter,
    transactionFilter,
    searchQuery,
    filterType,
    salePriceRange,
    jeonsePriceRange,
    monthlyPriceRange,
    areaRange,
    sortBy
  })

  // Use map hook for Kakao Map
  const { map, currentZoom } = useMap({
    mapRef,
    properties,
    transactionFilter,
    onPropertySelect: handlePropertyClick
  })

  // Update properties hook with map instance
  useEffect(() => {
    if (map) {
      // Setup zoom and drag listeners
      let zoomTimeoutId: NodeJS.Timeout | null = null
      let dragTimeoutId: NodeJS.Timeout | null = null

      const zoomChangeListener = () => {
        if (zoomTimeoutId) clearTimeout(zoomTimeoutId)
        zoomTimeoutId = setTimeout(() => {
          loadPropertiesFromAPI(map)
        }, 150)
      }

      const dragEndListener = () => {
        if (dragTimeoutId) clearTimeout(dragTimeoutId)
        dragTimeoutId = setTimeout(() => {
          loadPropertiesFromAPI(map)
        }, 300)
      }

      try {
        window.kakao.maps.event.addListener(map, "zoom_changed", zoomChangeListener)
        window.kakao.maps.event.addListener(map, "dragend", dragEndListener)

        return () => {
          if (zoomTimeoutId) clearTimeout(zoomTimeoutId)
          if (dragTimeoutId) clearTimeout(dragTimeoutId)
          window.kakao.maps.event.removeListener(map, "zoom_changed", zoomChangeListener)
          window.kakao.maps.event.removeListener(map, "dragend", dragEndListener)
        }
      } catch (error) {
        console.error('Error setting up map listeners:', error)
      }
    }
  }, [map, loadPropertiesFromAPI])

  // Resize map when sidebar is toggled
  useEffect(() => {
    if (map) {
      setTimeout(() => {
        try {
          map.relayout()
        } catch (error) {
          console.error('Error relayout map:', error)
        }
      }, 350)
    }
  }, [sidebarOpen, map])

  const handleSearch = () => {
    // Search is handled by useProperties hook automatically
  }

  const showAllAreas = useCallback(() => {
    if (map) {
      map.setCenter(new window.kakao.maps.LatLng(37.5095, 127.0628))
      map.setLevel(8)
    }
  }, [map])

  const showServiceAreas = useCallback(() => {
    if (map) {
      map.setCenter(new window.kakao.maps.LatLng(37.5095, 127.0628))
      map.setLevel(6)
    }
  }, [map])

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  return (
    <>
    <div className={`${isFullscreen ? "fixed inset-0 z-50" : ""} flex h-full bg-background relative`}>
      {/* Left Panel - Search and Filters */}
      <div
        className={`border-r border-border flex flex-col transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'w-80' : 'w-0 overflow-hidden'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border bg-primary">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-primary-foreground">
                {selectedProperty ? selectedProperty.name : "서울 강남3구 부동산 정보"}
              </h2>
              <p className="text-sm text-primary-foreground/80">
                {selectedProperty
                  ? `${selectedProperty.gu} ${selectedProperty.dong}`
                  : "서비스 가능 지역: 강남구, 서초구, 송파구"
                }
              </p>
            </div>
            {selectedProperty && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedProperty(null)}
                className="text-primary-foreground hover:bg-primary-foreground/20"
              >
                ✕
              </Button>
            )}
          </div>
        </div>

        {/* Search - Hide when showing property detail */}
        {!selectedProperty && (
        <div className="p-4 border-b border-border">
          <div className="flex gap-2 mb-3">
            <Input
              placeholder="단지명, 구, 동으로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
            <Button onClick={handleSearch} size="icon">
              <Search className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex gap-2 mb-3">
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="전체">전체 지역</SelectItem>
                {serviceAreas.map((area) => (
                  <SelectItem key={area} value={area}>
                    {area}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="이름순">이름순</SelectItem>
                <SelectItem value="가격순">가격순</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="text-sm text-muted-foreground">
            {loading ? (
              <span>로딩 중...</span>
            ) : (
              <span>총 {filteredProperties.length}개 매물</span>
            )}
          </div>
        </div>
        )}

        {/* Property List or Property Detail */}
        {selectedProperty ? (
          <div className="flex-1 overflow-y-auto p-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-xl">{selectedProperty.name}</CardTitle>
                <div className="text-sm text-muted-foreground">
                  {selectedProperty.gu} {selectedProperty.dong}
                </div>
                {selectedProperty.property_type && (
                  <Badge className="w-fit mt-2">{selectedProperty.property_type}</Badge>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 가격 정보 */}
                <div>
                  <h3 className="font-semibold mb-2 text-sm">가격 정보</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {selectedProperty.sale_max_price_eok && (
                      <div className="bg-red-50 p-2 rounded">
                        <div className="text-xs text-red-600">매매</div>
                        <div className="font-semibold">{selectedProperty.sale_max_price_eok}</div>
                      </div>
                    )}
                    {selectedProperty.jeonse_max_price_eok && (
                      <div className="bg-blue-50 p-2 rounded">
                        <div className="text-xs text-blue-600">전세</div>
                        <div className="font-semibold">{selectedProperty.jeonse_max_price_eok}</div>
                      </div>
                    )}
                    {selectedProperty.rent_max_price_eok && (
                      <div className="bg-green-50 p-2 rounded">
                        <div className="text-xs text-green-600">월세</div>
                        <div className="font-semibold">{selectedProperty.rent_max_price_eok}</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 단지 정보 */}
                {selectedProperty.total_households && (
                  <div>
                    <h3 className="font-semibold mb-2 text-sm">단지 정보</h3>
                    <div className="space-y-1 text-sm">
                      {selectedProperty.total_households && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">세대수</span>
                          <span className="font-medium">{selectedProperty.total_households}세대</span>
                        </div>
                      )}
                      {selectedProperty.total_buildings && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">동수</span>
                          <span className="font-medium">{selectedProperty.total_buildings}동</span>
                        </div>
                      )}
                      {selectedProperty.completion_date && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">준공</span>
                          <span className="font-medium">{selectedProperty.completion_date}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 주변 시설 정보 */}
                {(selectedProperty.nearby_subway_stations || selectedProperty.nearby_schools || selectedProperty.nearby_marts) && (
                  <div>
                    <h3 className="font-semibold mb-2 text-sm">주변 시설</h3>
                    <div className="space-y-3">
                      {/* Subway Stations */}
                      {selectedProperty.nearby_subway_stations && (() => {
                        try {
                          const stations = JSON.parse(selectedProperty.nearby_subway_stations)
                          if (stations && stations.length > 0) {
                            return (
                              <div>
                                <div className="text-xs font-medium text-blue-600 mb-1">지하철역</div>
                                {stations.slice(0, 3).map((station: any, idx: number) => (
                                  <div key={idx} className="text-sm flex justify-between py-1">
                                    <span>{station.name} ({station.line})</span>
                                    <span className="text-blue-600 font-semibold">{station.distance}m</span>
                                  </div>
                                ))}
                              </div>
                            )
                          }
                        } catch (e) {
                          console.error('Failed to parse subway stations:', e)
                        }
                        return null
                      })()}

                      {/* Schools */}
                      {selectedProperty.nearby_schools && (() => {
                        try {
                          const schools = JSON.parse(selectedProperty.nearby_schools)
                          if (schools && schools.length > 0) {
                            return (
                              <div>
                                <div className="text-xs font-medium text-green-600 mb-1">학교</div>
                                {schools.slice(0, 3).map((school: any, idx: number) => (
                                  <div key={idx} className="text-sm flex justify-between py-1">
                                    <span>{school.name}</span>
                                    <span className="text-green-600 font-semibold">{school.distance}m</span>
                                  </div>
                                ))}
                              </div>
                            )
                          }
                        } catch (e) {
                          console.error('Failed to parse schools:', e)
                        }
                        return null
                      })()}

                      {/* Marts */}
                      {selectedProperty.nearby_marts && (() => {
                        try {
                          const marts = JSON.parse(selectedProperty.nearby_marts)
                          if (marts && marts.length > 0) {
                            return (
                              <div>
                                <div className="text-xs font-medium text-orange-600 mb-1">편의시설</div>
                                {marts.slice(0, 3).map((mart: any, idx: number) => (
                                  <div key={idx} className="text-sm flex justify-between py-1">
                                    <span>{mart.name}</span>
                                    <span className="text-orange-600 font-semibold">{mart.distance}m</span>
                                  </div>
                                ))}
                              </div>
                            )
                          }
                        } catch (e) {
                          console.error('Failed to parse marts:', e)
                        }
                        return null
                      })()}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto" onScroll={handleScroll}>
            <div className="p-4 space-y-2">
              {displayedProperties.map((property) => (
                <Card
                  key={`${property.name}-${property.latitude}-${property.longitude}`}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => handlePropertyClick(property)}
                >
                  <CardContent className="p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h3 className="font-semibold text-sm mb-1">{property.name}</h3>
                        <p className="text-xs text-muted-foreground">
                          {property.gu} {property.dong}
                        </p>
                      </div>
                      {property.property_type && (
                        <Badge variant="outline" className="text-xs">
                          {property.property_type}
                        </Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-xs">
                      {property.sale_max_price_eok && (
                        <div className="bg-red-50 px-2 py-1 rounded text-center">
                          <div className="text-red-600 font-semibold">
                            {property.sale_max_price_eok}
                          </div>
                        </div>
                      )}
                      {property.jeonse_max_price_eok && (
                        <div className="bg-blue-50 px-2 py-1 rounded text-center">
                          <div className="text-blue-600 font-semibold">
                            {property.jeonse_max_price_eok}
                          </div>
                        </div>
                      )}
                      {property.rent_max_price_eok && (
                        <div className="bg-green-50 px-2 py-1 rounded text-center">
                          <div className="text-green-600 font-semibold">
                            {property.rent_max_price_eok}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
              {isLoadingMore && (
                <div className="text-center py-4 text-sm text-muted-foreground">
                  로딩 중...
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Toggle Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-border rounded-r-lg p-2 shadow-md hover:bg-gray-50 transition-all"
        style={{ left: sidebarOpen ? '320px' : '0px' }}
      >
        <svg
          className="w-5 h-5 text-gray-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {sidebarOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          )}
        </svg>
      </button>

      {/* Right Panel - Map */}
      <div className="flex-1 relative">
        <div className="w-full h-full relative overflow-hidden">
          <div ref={mapRef} className="w-full h-full" />

          {/* Map Filter Controls */}
          <div className="absolute top-4 left-4 z-10 flex gap-2">
            {/* Property Type Filter */}
            <Select value={propertyTypeFilter} onValueChange={setPropertyTypeFilter}>
              <SelectTrigger className="w-[240px] bg-white shadow-md border-0 h-10 font-medium">
                <SelectValue placeholder="아파트, 오피스텔, 빌라, 단독/다가구" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="전체">전체 유형</SelectItem>
                <SelectItem value="아파트">아파트</SelectItem>
                <SelectItem value="오피스텔">오피스텔</SelectItem>
                <SelectItem value="빌라">빌라</SelectItem>
                <SelectItem value="단독/다가구">단독/다가구</SelectItem>
              </SelectContent>
            </Select>

            {/* Transaction Type Filter */}
            <Select value={transactionFilter} onValueChange={setTransactionFilter}>
              <SelectTrigger className="w-[140px] bg-white shadow-md border-0 h-10 font-medium">
                <SelectValue placeholder="매매, 전세, 월세" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="매매">매매</SelectItem>
                <SelectItem value="전세">전세</SelectItem>
                <SelectItem value="월세">월세</SelectItem>
                <SelectItem value="전체">매매, 전세, 월세</SelectItem>
              </SelectContent>
            </Select>

            {/* Price Filter Inline Panel */}
            <div className="relative">
              <Button
                variant="outline"
                className="bg-white shadow-md border-0 h-10 px-4 font-medium hover:bg-white text-black hover:text-black"
                onClick={() => {
                  setPriceFilterOpen(!priceFilterOpen)
                  setAreaFilterOpen(false)
                }}
              >
                실거래 가격
              </Button>

              {priceFilterOpen && (
                <div className="absolute top-full left-0 mt-2 w-[400px] bg-white shadow-lg rounded-lg border p-4 z-20">
                  <div className="space-y-6">
                    {/* Sale Price Range */}
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium">매매가</span>
                        <span className="text-sm text-muted-foreground">
                          {salePriceRange[0]}억 ~ {salePriceRange[1] >= 50 ? '50억 이상' : `${salePriceRange[1]}억`}
                        </span>
                      </div>
                      <Slider
                        value={salePriceRange}
                        onValueChange={(value) => setSalePriceRange(value as [number, number])}
                        max={50}
                        step={1}
                        className="mb-2"
                      />
                    </div>

                    {/* Jeonse Price Range */}
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium">전세가</span>
                        <span className="text-sm text-muted-foreground">
                          {jeonsePriceRange[0]}억 ~ {jeonsePriceRange[1] >= 20 ? '20억 이상' : `${jeonsePriceRange[1]}억`}
                        </span>
                      </div>
                      <Slider
                        value={jeonsePriceRange}
                        onValueChange={(value) => setJeonsePriceRange(value as [number, number])}
                        max={20}
                        step={1}
                        className="mb-2"
                      />
                    </div>

                    {/* Monthly Rent Price Range */}
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium">월세 (보증금)</span>
                        <span className="text-sm text-muted-foreground">
                          {monthlyPriceRange[0]}억 ~ {monthlyPriceRange[1] >= 10 ? '10억 이상' : `${monthlyPriceRange[1]}억`}
                        </span>
                      </div>
                      <Slider
                        value={monthlyPriceRange}
                        onValueChange={(value) => setMonthlyPriceRange(value as [number, number])}
                        max={10}
                        step={0.5}
                        className="mb-2"
                      />
                    </div>

                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" onClick={() => {
                        setSalePriceRange([0, 50])
                        setJeonsePriceRange([0, 20])
                        setMonthlyPriceRange([0, 10])
                      }}>
                        초기화
                      </Button>
                      <Button size="sm" onClick={() => setPriceFilterOpen(false)}>
                        적용
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Area Filter Inline Panel */}
            <div className="relative">
              <Button
                variant="outline"
                className="bg-white shadow-md border-0 h-10 px-4 font-medium hover:bg-white text-black hover:text-black"
                onClick={() => {
                  setAreaFilterOpen(!areaFilterOpen)
                  setPriceFilterOpen(false)
                }}
              >
                면적
              </Button>

              {areaFilterOpen && (
                <div className="absolute top-full left-0 mt-2 w-[300px] bg-white shadow-lg rounded-lg border p-4 z-20">
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium">면적 (평)</span>
                        <span className="text-sm text-muted-foreground">
                          {areaRange[0]}평 ~ {areaRange[1] >= 70 ? '70평 이상' : `${areaRange[1]}평`}
                        </span>
                      </div>
                      <Slider
                        value={areaRange}
                        onValueChange={(value) => setAreaRange(value as [number, number])}
                        max={70}
                        step={5}
                        className="mb-2"
                      />
                    </div>

                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" onClick={() => setAreaRange([0, 70])}>
                        초기화
                      </Button>
                      <Button size="sm" onClick={() => setAreaFilterOpen(false)}>
                        적용
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Map Control Buttons */}
          <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
            <Button
              variant="outline"
              size="sm"
              className="bg-white shadow-md border-0"
              onClick={showServiceAreas}
            >
              서비스 지역
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-white shadow-md border-0"
              onClick={showAllAreas}
            >
              전체 보기
            </Button>
          </div>

          {/* Map Legend */}
          <div className="absolute bottom-4 left-4 z-10 bg-white shadow-lg rounded-lg border p-3">
            <div className="text-xs font-semibold mb-2">거래 유형</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span>매매</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span>전세</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span>월세</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <FloatingChatButton />
    </>
  )
}
