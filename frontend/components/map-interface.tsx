"use client"

import { AIRiskAnalysis } from "./map-interface/ai-risk-analysis"
import { useState, useRef, useCallback, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, Train, School, ShoppingBasket, X, MapPin, Building2, Home, ChevronLeft } from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { getAllDistrictNames } from "@/lib/district-coordinates"
import { useMap } from "./map-interface/use-map"
import { useProperties } from "./map-interface/use-properties"
import { formatPriceInEok } from "./map-interface/price-utils"
import { ScrollArea } from "@/components/ui/scroll-area"

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
    onPropertySelect: (property) => {
      handlePropertyClick(property)
      // 매물 선택 시 사이드바 자동으로 열기
      if (!sidebarOpen) {
        setSidebarOpen(true)
      }
    }
  })

  // Update properties hook with map instance
  // Update properties hook with map instance and handle initial load / filter changes
  useEffect(() => {
    if (map) {
      // Initial load with a slight delay to ensure map is ready and layout is correct
      const initialLoadTimer = setTimeout(() => {
        try {
          map.relayout()
          loadPropertiesFromAPI(map)
        } catch (error) {
          console.error('Error during initial map load:', error)
        }
      }, 500)

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
          clearTimeout(initialLoadTimer)
          if (zoomTimeoutId) clearTimeout(zoomTimeoutId)
          if (dragTimeoutId) clearTimeout(dragTimeoutId)
          window.kakao.maps.event.removeListener(map, "zoom_changed", zoomChangeListener)
          window.kakao.maps.event.removeListener(map, "dragend", dragEndListener)
        }
      } catch (error) {
        console.error('Error setting up map listeners:', error)
      }
    }
  }, [map, loadPropertiesFromAPI, filterType, transactionFilter, propertyTypeFilter, salePriceRange, jeonsePriceRange, monthlyPriceRange, areaRange])

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

  // Helper to get property type color
  const getPropertyTypeColor = (type: string) => {
    if (type === "아파트") return "bg-blue-100 text-blue-700 border-blue-200"
    if (type === "오피스텔") return "bg-purple-100 text-purple-700 border-purple-200"
    if (type === "빌라") return "bg-orange-100 text-orange-700 border-orange-200"
    return "bg-gray-100 text-gray-700 border-gray-200"
  }

  return (
    <>
      <div className={`${isFullscreen ? "fixed inset-0 z-50" : ""} flex h-full bg-background relative`}>
        {/* Left Panel - Search and Filters */}
        <div
          className={`border-r border-border flex flex-col transition-all duration-300 ease-in-out bg-white z-20 shadow-xl ${sidebarOpen ? 'w-[400px]' : 'w-0 overflow-hidden'
            } `}
        >
          {/* Header */}
          <div className="p-5 border-b border-border bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight">
                  {selectedProperty ? "매물 상세 정보" : "서울 강남3구 부동산"}
                </h2>
                <p className="text-xs text-sidebar-primary-foreground/80 mt-1 opacity-90">
                  {selectedProperty
                    ? `${selectedProperty.gu} ${selectedProperty.dong} `
                    : "강남구 · 서초구 · 송파구 실거래가"
                  }
                </p>
              </div>
              {selectedProperty && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedProperty(null)}
                  className="text-sidebar-primary-foreground hover:bg-white/20 rounded-full"
                >
                  <X className="h-5 w-5" />
                </Button>
              )}
            </div>
          </div>

          {/* Search - Hide when showing property detail */}
          {!selectedProperty && (
            <div className="p-4 border-b border-border bg-slate-50/50">
              <div className="flex gap-2 mb-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="지역, 지하철역, 단지명 검색"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 bg-white border-slate-200 focus-visible:ring-slate-400"
                  />
                </div>
              </div>

              <div className="flex gap-2 mb-3">
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="flex-1 bg-white border-slate-200">
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
                  <SelectTrigger className="w-32 bg-white border-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="이름순">이름순</SelectItem>
                    <SelectItem value="가격순">가격순</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                <span>총 <span className="font-bold text-slate-900">{filteredProperties.length.toLocaleString()}</span>개 매물</span>
                {loading && <span className="animate-pulse">데이터 불러오는 중...</span>}
              </div>
            </div>
          )}

          {/* Property List or Property Detail */}
          {selectedProperty ? (
            <ScrollArea className="flex-1 bg-slate-50">
              <div className="p-4 pb-20">
                <Card className="border-0 shadow-none bg-transparent">
                  <CardHeader className="p-0 mb-6">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <Badge className={`mb-2 hover:bg-opacity-100 ${getPropertyTypeColor(selectedProperty.property_type || '아파트')} border-0`}>
                          {selectedProperty.property_type || '아파트'}
                        </Badge>
                        <CardTitle className="text-2xl font-bold text-slate-900 leading-tight">
                          {selectedProperty.name}
                        </CardTitle>
                        <div className="flex items-center text-slate-500 mt-2 text-sm">
                          <MapPin className="h-3.5 w-3.5 mr-1" />
                          {selectedProperty.gu} {selectedProperty.dong}
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-0 space-y-6">
                    {/* 가격 정보 Cards */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                        <span className="text-xs text-slate-500 font-medium mb-1">매매</span>
                        <span className={`font-bold ${selectedProperty.sale_max_price_eok ? 'text-slate-900' : 'text-slate-300'} `}>
                          {selectedProperty.sale_max_price_eok || '-'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                        <span className="text-xs text-slate-500 font-medium mb-1">전세</span>
                        <span className={`font-bold ${selectedProperty.jeonse_max_price_eok ? 'text-slate-900' : 'text-slate-300'} `}>
                          {selectedProperty.jeonse_max_price_eok || '-'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                        <span className="text-xs text-slate-500 font-medium mb-1">월세</span>
                        <span className={`font-bold ${selectedProperty.rent_max_price_eok ? 'text-slate-900' : 'text-slate-300'} `}>
                          {selectedProperty.rent_max_price_eok || '-'}
                        </span>
                      </div>
                    </div>

                    {/* 단지 정보 */}
                    {(selectedProperty.total_households || selectedProperty.completion_date) && (
                      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
                        <h3 className="font-semibold text-slate-900 mb-3 flex items-center">
                          <Building2 className="h-4 w-4 mr-2 text-slate-500" />
                          단지 정보
                        </h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          {selectedProperty.total_households && (
                            <div className="flex flex-col">
                              <span className="text-xs text-slate-500">세대수</span>
                              <span className="font-medium text-slate-900">{selectedProperty.total_households}세대</span>
                            </div>
                          )}
                          {selectedProperty.total_buildings && (
                            <div className="flex flex-col">
                              <span className="text-xs text-slate-500">동수</span>
                              <span className="font-medium text-slate-900">{selectedProperty.total_buildings}동</span>
                            </div>
                          )}
                          {selectedProperty.completion_date && (
                            <div className="flex flex-col">
                              <span className="text-xs text-slate-500">준공일</span>
                              <span className="font-medium text-slate-900">{selectedProperty.completion_date}</span>
                            </div>
                          )}
                          {selectedProperty.area_summary && (
                            <div className="flex flex-col">
                              <span className="text-xs text-slate-500">면적</span>
                              <span className="font-medium text-slate-900 truncate" title={selectedProperty.area_summary}>
                                {selectedProperty.area_summary}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 주변 시설 정보 */}
                    {(selectedProperty.nearby_subway_stations || selectedProperty.nearby_schools || selectedProperty.nearby_marts) && (
                      <div className="space-y-4">
                        <h3 className="font-semibold text-slate-900 flex items-center px-1">
                          <MapPin className="h-4 w-4 mr-2 text-slate-500" />
                          주변 편의시설
                        </h3>

                        {/* Subway Stations */}
                        {selectedProperty.nearby_subway_stations && (() => {
                          try {
                            const stations = JSON.parse(selectedProperty.nearby_subway_stations)
                            // Helper functions (same as before but cleaner)
                            const getLineName = (station: any) => {
                              if (station.category) {
                                const parts = station.category.split('>')
                                const lastPart = parts[parts.length - 1].trim()
                                if (lastPart.endsWith('호선') || lastPart.endsWith('선')) return lastPart
                              }
                              return ''
                            }
                            const getSubwayIcon = (line: string) => {
                              const lineMap: Record<string, string> = {
                                "수도권1호선": "/images/subway_img/line_1.svg",
                                "수도권2호선": "/images/subway_img/line_2.svg",
                                "수도권3호선": "/images/subway_img/line_3.svg",
                                "수도권4호선": "/images/subway_img/line_4.svg",
                                "수도권5호선": "/images/subway_img/line_5.svg",
                                "수도권6호선": "/images/subway_img/line_6.svg",
                                "수도권7호선": "/images/subway_img/line_7.svg",
                                "수도권8호선": "/images/subway_img/line_8.svg",
                                "수도권9호선": "/images/subway_img/line_9.svg",
                                "신분당선": "/images/subway_img/line_sinbundang.svg",
                                "수인분당선": "/images/subway_img/line_suin.svg",
                              }
                              return lineMap[line] || null
                            }
                            const getWalkingTime = (distance: number) => `${distance} m / 도보 ${Math.ceil(distance / 80)} 분`
                            const getCleanStationName = (name: string, line: string) => {
                              let cleaned = name
                              if (line) cleaned = cleaned.replace(line, '')
                              cleaned = cleaned.replace(/\s*\d+호선$/, '').replace(/\s*[가-힣]+선$/, '')
                              return cleaned.trim()
                            }

                            if (stations && stations.length > 0) {
                              return (
                                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
                                  <div className="flex items-center gap-2 mb-3 text-sm font-medium text-slate-700">
                                    <Train className="h-4 w-4 text-blue-500" />
                                    지하철역
                                  </div>
                                  <div className="space-y-3">
                                    {stations.slice(0, 3).map((station: any, idx: number) => {
                                      const lineName = getLineName(station)
                                      const iconPath = getSubwayIcon(lineName)
                                      const cleanName = getCleanStationName(station.name, lineName)
                                      return (
                                        <div key={idx} className="flex items-center justify-between text-sm">
                                          <div className="flex items-center gap-2">
                                            {iconPath ? (
                                              <img src={iconPath} alt={lineName} className="h-4 w-auto object-contain"
                                                onError={(e) => { e.currentTarget.style.display = 'none'; const fallback = e.currentTarget.parentElement?.lastElementChild; if (fallback) fallback.classList.remove('hidden'); }} />
                                            ) : null}
                                            <span className="font-medium text-slate-700">{cleanName}</span>
                                            <span className={`text-xs text-slate-400 ${iconPath ? 'hidden' : ''} `}>{lineName}</span>
                                          </div>
                                          <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-1 rounded-full">{getWalkingTime(station.distance)}</span>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              )
                            }
                          } catch (e) { return null }
                          return null
                        })()}

                        {/* Schools */}
                        {selectedProperty.nearby_schools && (() => {
                          try {
                            const schools = JSON.parse(selectedProperty.nearby_schools)
                            const getWalkingTime = (distance: number) => `${distance} m / 도보 ${Math.ceil(distance / 80)} 분`
                            if (schools && schools.length > 0) {
                              return (
                                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
                                  <div className="flex items-center gap-2 mb-3 text-sm font-medium text-slate-700">
                                    <School className="h-4 w-4 text-green-500" />
                                    학교
                                  </div>
                                  <div className="space-y-3">
                                    {schools.slice(0, 3).map((school: any, idx: number) => (
                                      <div key={idx} className="flex items-center justify-between text-sm">
                                        <span className="font-medium text-slate-700">{school.name}</span>
                                        <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-1 rounded-full">{getWalkingTime(school.distance)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )
                            }
                          } catch (e) { return null }
                          return null
                        })()}

                        {/* Marts */}
                        {selectedProperty.nearby_marts && (() => {
                          try {
                            const marts = JSON.parse(selectedProperty.nearby_marts)
                            const getDrivingTime = (distance: number) => `${distance} m / 차량 ${Math.ceil(distance / 400)} 분`
                            if (marts && marts.length > 0) {
                              return (
                                <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
                                  <div className="flex items-center gap-2 mb-3 text-sm font-medium text-slate-700">
                                    <ShoppingBasket className="h-4 w-4 text-orange-500" />
                                    편의시설
                                  </div>
                                  <div className="space-y-3">
                                    {marts.slice(0, 3).map((mart: any, idx: number) => (
                                      <div key={idx} className="flex items-center justify-between text-sm">
                                        <span className="font-medium text-slate-700">{mart.name}</span>
                                        <span className="text-xs text-orange-600 font-medium bg-orange-50 px-2 py-1 rounded-full">{getDrivingTime(mart.distance)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )
                            }
                          } catch (e) { return null }
                          return null
                        })()}
                      </div>
                    )}
                  </CardContent>
                </Card>
                <AIRiskAnalysis />
              </div>
            </ScrollArea>
          ) : (
            <div className="flex-1 overflow-y-auto bg-slate-50" onScroll={handleScroll}>
              <div className="p-3 space-y-2">
                {displayedProperties.map((property) => (
                  <Card
                    key={`${property.name} -${property.latitude} -${property.longitude} `}
                    className="cursor-pointer hover:shadow-lg transition-all duration-200 border border-slate-200 hover:border-slate-300 group bg-white"
                    onClick={() => {
                      handlePropertyClick(property)
                      if (map) {
                        const moveLatLon = new window.kakao.maps.LatLng(property.latitude, property.longitude)
                        map.setLevel(1)
                        map.panTo(moveLatLon)
                      }
                    }}
                  >
                    <CardContent className="p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 h-5 ${getPropertyTypeColor(property.property_type || '아파트')} border-0 bg-opacity-50`}>
                              {property.property_type || '아파트'}
                            </Badge>
                          </div>
                          <h3 className="font-bold text-base text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1">
                            {property.name}
                          </h3>
                          <p className="text-xs text-slate-500 mt-0.5 flex items-center">
                            <MapPin className="h-3 w-3 mr-0.5 inline" />
                            {property.gu} {property.dong}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs mt-2">
                        {property.sale_max_price_eok && (
                          <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                            <span className="text-slate-500 font-medium">매매</span>
                            <span className="text-slate-900 font-bold">{property.sale_max_price_eok}</span>
                          </div>
                        )}
                        {property.jeonse_max_price_eok && (
                          <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                            <span className="text-slate-500 font-medium">전세</span>
                            <span className="text-slate-900 font-bold">{property.jeonse_max_price_eok}</span>
                          </div>
                        )}
                        {property.rent_max_price_eok && (
                          <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                            <span className="text-slate-500 font-medium">월세</span>
                            <span className="text-slate-900 font-bold">{property.rent_max_price_eok}</span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {isLoadingMore && (
                  <div className="text-center py-6">
                    <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-current border-r-transparent align-[-0.125em] text-blue-600 motion-reduce:animate-[spin_1.5s_linear_infinite]" />
                  </div>
                )}

              </div>
            </div>
          )}
        </div>

        {/* Sidebar Toggle Button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-border rounded-r-lg p-2 shadow-md hover:bg-gray-50 transition-all duration-300 ease-in-out"
          style={{ left: sidebarOpen ? '400px' : '0px' }}
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
                            {salePriceRange[0]}억 ~ {salePriceRange[1] >= 50 ? '50억 이상' : `${salePriceRange[1]} 억`}
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
                            {jeonsePriceRange[0]}억 ~ {jeonsePriceRange[1] >= 20 ? '20억 이상' : `${jeonsePriceRange[1]} 억`}
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
                            {monthlyPriceRange[0]}억 ~ {monthlyPriceRange[1] >= 10 ? '10억 이상' : `${monthlyPriceRange[1]} 억`}
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
                            {areaRange[0]}평 ~ {areaRange[1] >= 70 ? '70평 이상' : `${areaRange[1]} 평`}
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

            {/* Map Control Buttons - 우측 하단으로 이동 */}
            <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-2">
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
    </>
  )
}
