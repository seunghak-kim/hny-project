"use client"

import { useState, useEffect, useRef, useMemo, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, Maximize2, Minimize2, X } from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { getDistrictCoordinatesNew, getDistrictCenterNew, getAllDistrictNames } from "@/lib/district-coordinates"
import { clusterProperties, getClusterStyle, createDetailedMarkerContent, createClusterMarkerContent, type Cluster } from "@/lib/clustering"
import { FloatingChatButton } from "@/components/floating-chat-button"

declare global {
  interface Window {
    kakao: any
  }
}

interface PropertyData {
  단지명: string
  구: string
  동: string
  // 가격 정보 - 억원 표시용 (포맷된 문자열)
  매매_최저가_억원?: string
  매매_최고가_억원?: string
  전세_최저가_억원?: string
  전세_최고가_억원?: string
  월세_최저가_억원?: string
  월세_최고가_억원?: string
  // 가격 정보 - Raw values in 만원 units (for calculations)
  매매_최저가?: string
  매매_최고가?: string
  전세_최저가?: string
  전세_최고가?: string
  월세_최저가?: string
  월세_최고가?: string
  단지요약: string
  총_거래건수: string
  면적요약: string
  세대수: string
  동수: string
  준공년월: string
  위도?: number
  경도?: number
  type?: "office" | "residential"
  유형?: string  // 부동산 유형 (아파트, 오피스텔, 빌라, 단독/다가구, 원룸 등)
}

export function MapInterface() {
  const mapRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedProperty, setSelectedProperty] = useState<PropertyData | null>(null)
  const [filterType, setFilterType] = useState<string>("전체")
  const [transactionFilter, setTransactionFilter] = useState<string>("전체")
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

  // Selected quick filters
  const [selectedPyeongFilter, setSelectedPyeongFilter] = useState<string | null>(null)
  const [markers, setMarkers] = useState<any[]>([])
  const [polygons, setPolygons] = useState<any[]>([])
  const [currentZoom, setCurrentZoom] = useState(7)
  const [properties, setProperties] = useState<PropertyData[]>([]) // 지도 렌더링용 (viewport 기반)
  const [allProperties, setAllProperties] = useState<PropertyData[]>([]) // 사이드바 검색용 (전체 매물)
  const [loading, setLoading] = useState(true)
  const [displayedProperties, setDisplayedProperties] = useState<PropertyData[]>([])
  const [itemsToShow, setItemsToShow] = useState(20)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // 서비스 가능 지역 목록
  const serviceAreas = getAllDistrictNames()

  // Transform API response to PropertyData format (공통 함수)
  const transformAPIResponse = (data: any[]): PropertyData[] => {
    return data
      .filter((item: any) => {
        // 0원 데이터 필터링: 모든 가격이 0이거나 없는 매물 제외
        const hasSalePrice = item.매매_최고가 && parseFloat(item.매매_최고가) > 0
        const hasJeonsePrice = item.전세_최고가 && parseFloat(item.전세_최고가) > 0
        const hasMonthlyPrice = item.월세_최고가 && parseFloat(item.월세_최고가) > 0

        // 최소 하나의 가격 정보는 있어야 함
        return hasSalePrice || hasJeonsePrice || hasMonthlyPrice
      })
      .map((item: any) => ({
        단지명: item.단지명,
        구: item.구 || "",
        동: item.동 || "",
        위도: item.위도,
        경도: item.경도,
        단지요약: "",
        총_거래건수: item.총_거래건수?.toString() || "0",
        면적요약: item.면적요약 || "",
        세대수: item.세대수?.toString() || "",
        동수: item.동수?.toString() || "",
        준공년월: item.준공년월 || "",
        매매_최저가_억원: item.매매_최저가_억원 || "",
        매매_최고가_억원: item.매매_최고가_억원 || "",
        전세_최저가_억원: item.전세_최저가_억원 || "",
        전세_최고가_억원: item.전세_최고가_억원 || "",
        월세_최저가_억원: item.월세_최저가_억원 || "",
        월세_최고가_억원: item.월세_최고가_억원 || "",
        매매_최저가: item.매매_최저가?.toString() || "",
        매매_최고가: item.매매_최고가?.toString() || "",
        전세_최저가: item.전세_최저가?.toString() || "",
        전세_최고가: item.전세_최고가?.toString() || "",
        월세_최저가: item.월세_최저가?.toString() || "",
        월세_최고가: item.월세_최고가?.toString() || "",
        유형: item.유형 || "아파트",
        type: "residential"
      }))
  }

  // Load ALL properties for sidebar search (전체 매물)
  const loadAllPropertiesFromAPI = useCallback(async () => {
    try {
      // 전체 매물을 가져오기 위해 서울 전체 범위 사용
      const params = new URLSearchParams({
        south: "37.4",
        north: "37.7",
        west: "126.8",
        east: "127.2",
        limit: "10000", // 전체 매물 - 제한 해제
      })

      // Add filters
      if (propertyTypeFilter !== "전체") {
        const typeMapping: { [key: string]: string } = {
          "아파트": "apartment",
          "오피스텔": "officetel",
          "빌라": "villa",
          "원룸": "oneroom",
          "단독/다가구": "house"
        }
        const apiType = typeMapping[propertyTypeFilter]
        if (apiType) {
          params.append("property_types", apiType)
        }
      }

      if (transactionFilter !== "전체") {
        const transactionMapping: { [key: string]: string } = {
          "매매": "sale",
          "전세": "jeonse",
          "월세": "rent"
        }
        const apiTransactionType = transactionMapping[transactionFilter]
        if (apiTransactionType) {
          params.append("transaction_type", apiTransactionType)
        }
      }

      const response = await fetch(`http://localhost:8000/api/real-estate/properties?${params}`)
      const data = await response.json()
      setAllProperties(transformAPIResponse(data))
    } catch (error) {
      console.error("Error loading all properties from API:", error)
      setAllProperties([])
    }
  }, [propertyTypeFilter, transactionFilter])

  // Load property data from API based on map viewport (지도 렌더링용)
  const loadPropertiesFromAPI = useCallback(async (mapInstance: any) => {
    if (!mapInstance) return

    try {
      setLoading(true)

      // Get map bounds
      const bounds = mapInstance.getBounds()
      const swLatLng = bounds.getSouthWest()
      const neLatLng = bounds.getNorthEast()

      // Get current zoom level
      const zoom = mapInstance.getLevel()

      // 줌 레벨 6 이상일 때는 강남구/서초구/송파구 전체 영역 데이터 로드
      let params: URLSearchParams
      if (zoom >= 6) {
        // 강남3구 전체 범위 (고정)
        params = new URLSearchParams({
          south: "37.4",      // 서초구 남단
          north: "37.58",     // 강남구 북단
          west: "126.98",     // 서초구 서단
          east: "127.15",     // 송파구 동단
          zoom: zoom.toString(),
          limit: "5000",      // 전체 데이터
        })
      } else {
        // 줌 레벨 5 이하일 때는 viewport 기반
        params = new URLSearchParams({
          south: swLatLng.getLat().toString(),
          north: neLatLng.getLat().toString(),
          west: swLatLng.getLng().toString(),
          east: neLatLng.getLng().toString(),
          zoom: zoom.toString(),
          limit: "1000",
        })
      }

      // Add filters
      if (propertyTypeFilter !== "전체") {
        const typeMapping: { [key: string]: string } = {
          "아파트": "apartment",
          "오피스텔": "officetel",
          "빌라": "villa",
          "원룸": "oneroom",
          "단독/다가구": "house"
        }
        const apiType = typeMapping[propertyTypeFilter]
        if (apiType) {
          params.append("property_types", apiType)
        }
      }

      if (transactionFilter !== "전체") {
        const transactionMapping: { [key: string]: string } = {
          "매매": "sale",
          "전세": "jeonse",
          "월세": "rent"
        }
        const apiTransactionType = transactionMapping[transactionFilter]
        if (apiTransactionType) {
          params.append("transaction_type", apiTransactionType)
        }
      }

      // Fetch from API
      const response = await fetch(`http://localhost:8000/api/real-estate/properties?${params}`)
      const data = await response.json()

      setProperties(transformAPIResponse(data))
    } catch (error) {
      console.error("Error loading property data from API:", error)
      setProperties([])
    } finally {
      setLoading(false)
    }
  }, [propertyTypeFilter, transactionFilter])

  // Load all properties for sidebar search (초기 로딩)
  useEffect(() => {
    loadAllPropertiesFromAPI()
  }, [loadAllPropertiesFromAPI])

  // Load properties when map is first created
  useEffect(() => {
    if (map) {
      loadPropertiesFromAPI(map)
    }
  }, [map]) // Only load once when map is created

  // Reload properties when filters change
  useEffect(() => {
    if (map) {
      loadPropertiesFromAPI(map)
    }
    // Also reload all properties for sidebar
    loadAllPropertiesFromAPI()
  }, [propertyTypeFilter, transactionFilter, loadPropertiesFromAPI, loadAllPropertiesFromAPI]) // Reload when filters change

  // Filter properties based on search and filters - optimized with useMemo
  // 사이드바 검색은 allProperties 사용 (전체 매물)
  const filteredProperties = useMemo(() => {
    let filtered = allProperties

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (property) =>
          property.단지명.toLowerCase().includes(searchQuery.toLowerCase()) ||
          property.구.includes(searchQuery) ||
          property.동.includes(searchQuery)
      )
    }

    // District filter
    if (filterType !== "전체") {
      filtered = filtered.filter((property) => property.구 === filterType)
    }

    // Property type filter
    if (propertyTypeFilter !== "전체") {
      filtered = filtered.filter((property) => {
        const propertyType = property.유형 || (property.type === 'office' ? '오피스텔' : '아파트')

        if (propertyTypeFilter === "아파트") {
          return propertyType === "아파트" || propertyType === "APT"
        } else if (propertyTypeFilter === "오피스텔") {
          return propertyType === "오피스텔" || propertyType === "OPST"
        } else if (propertyTypeFilter === "빌라") {
          return propertyType === "빌라" || propertyType.includes("빌라")
        } else if (propertyTypeFilter === "단독/다가구") {
          return propertyType === "단독/다가구" || propertyType.includes("단독") || propertyType.includes("다가구")
        } else if (propertyTypeFilter === "원룸") {
          return propertyType === "원룸"
        }
        return true
      })
    }

    // Transaction type filter - use raw 만원 values
    if (transactionFilter !== "전체") {
      filtered = filtered.filter((property) => {
        if (transactionFilter === "매매") {
          const salePrice = property.매매_최고가
          return salePrice && salePrice !== '' && salePrice !== '0' && parseFloat(salePrice) > 0
        } else if (transactionFilter === "전세") {
          const jeonsePrice = property.전세_최고가
          return jeonsePrice && jeonsePrice !== '' && jeonsePrice !== '0' && parseFloat(jeonsePrice) > 0
        } else if (transactionFilter === "월세") {
          const monthlyPrice = property.월세_최고가
          return monthlyPrice && monthlyPrice !== '' && monthlyPrice !== '0' && parseFloat(monthlyPrice) > 0
        }
        return true
      })
    }

    // Price range filter - only apply if ranges are not at default max values
    const isPriceFilterActive =
      salePriceRange[1] < 50 || salePriceRange[0] > 0 ||
      jeonsePriceRange[1] < 20 || jeonsePriceRange[0] > 0 ||
      monthlyPriceRange[1] < 10 || monthlyPriceRange[0] > 0

    if (isPriceFilterActive) {
      filtered = filtered.filter((property) => {
        let matchesFilter = false

        // Check sale price - convert from 만원 to 억원
        const salePrice = property.매매_최고가
        if (salePrice && salePrice !== '' && salePrice !== '0') {
          const priceInEok = parseFloat(salePrice) / 10000
          if (priceInEok >= salePriceRange[0] && priceInEok <= salePriceRange[1]) {
            matchesFilter = true
          }
        }

        // Check jeonse price - convert from 만원 to 억원
        const jeonsePrice = property.전세_최고가
        if (jeonsePrice && jeonsePrice !== '' && jeonsePrice !== '0') {
          const priceInEok = parseFloat(jeonsePrice) / 10000
          if (priceInEok >= jeonsePriceRange[0] && priceInEok <= jeonsePriceRange[1]) {
            matchesFilter = true
          }
        }

        // Check monthly price - convert from 만원 to 억원
        const monthlyPrice = property.월세_최고가
        if (monthlyPrice && monthlyPrice !== '' && monthlyPrice !== '0') {
          const priceInEok = parseFloat(monthlyPrice) / 10000
          if (priceInEok >= monthlyPriceRange[0] && priceInEok <= monthlyPriceRange[1]) {
            matchesFilter = true
          }
        }

        return matchesFilter
      })
    }

    // Area filter - only apply if not at default range
    const isAreaFilterActive = areaRange[0] > 0 || areaRange[1] < 70

    if (isAreaFilterActive) {
      filtered = filtered.filter((property) => {
        const areaStr = property.면적요약
        if (!areaStr) return true // Don't filter out if no area info

        // Extract area in pyeong from string like "84㎡(25평)" or "25평"
        const pyeongMatch = areaStr.match(/(\d+(?:\.\d+)?)평/)
        if (pyeongMatch) {
          const pyeong = parseFloat(pyeongMatch[1])
          return pyeong >= areaRange[0] && pyeong <= areaRange[1]
        }

        // Try to extract from square meters
        const sqmMatch = areaStr.match(/(\d+(?:\.\d+)?)㎡/)
        if (sqmMatch) {
          const sqm = parseFloat(sqmMatch[1])
          const pyeong = sqm / 3.3058 // Convert to pyeong
          return pyeong >= areaRange[0] && pyeong <= areaRange[1]
        }

        return true // Don't filter out if can't parse area
      })
    }

    return filtered
  }, [allProperties, searchQuery, filterType, propertyTypeFilter, transactionFilter, salePriceRange, jeonsePriceRange, monthlyPriceRange, areaRange])

  // Reset pagination when filters change
  useEffect(() => {
    setItemsToShow(20)
  }, [filteredProperties])

  // Update displayed properties when filteredProperties or itemsToShow changes
  useEffect(() => {
    setDisplayedProperties(filteredProperties.slice(0, itemsToShow))
  }, [filteredProperties, itemsToShow])

  // Infinite scroll handler
  const loadMoreProperties = () => {
    if (isLoadingMore || itemsToShow >= filteredProperties.length) return
    
    setIsLoadingMore(true)
    setTimeout(() => {
      setItemsToShow(prev => Math.min(prev + 20, filteredProperties.length))
      setIsLoadingMore(false)
    }, 500)
  }

  // Scroll event handler
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    
    if (scrollHeight - scrollTop <= clientHeight + 100) {
      loadMoreProperties()
    }
  }

  const handleSearch = () => {
    // Search is handled by useEffect above
  }

  const handlePropertyClick = (property: PropertyData) => {
    setSelectedProperty(property)
    // Center map on selected property
    if (map && property.위도 && property.경도) {
      const position = new window.kakao.maps.LatLng(property.위도, property.경도)
      map.setCenter(position)
    }
  }

  const getTrustScoreColor = (score: number) => {
    if (score >= 90) return "bg-green-500"
    if (score >= 70) return "bg-yellow-500"
    return "bg-red-500"
  }

  // Format monthly rent price (raw value in 만원 units)
  const formatMonthlyPrice = (priceInManwon: number): string => {
    if (priceInManwon >= 10000) {
      // Convert to 억 if >= 1억 (10,000만원)
      const eok = priceInManwon / 10000
      // Remove .0 decimal for whole numbers (e.g., 9.0억 → 9억)
      return eok % 1 === 0 ? `${Math.round(eok)}억원` : `${eok.toFixed(1)}억원`
    }
    // Display in 만원 with thousand separators
    return `${Math.round(priceInManwon).toLocaleString()}만원`
  }

  useEffect(() => {
    if (typeof window === 'undefined' || !mapRef.current) return

    if (window.kakao && window.kakao.maps) {
      initializeMap()
      return
    }

    const script = document.createElement("script")
    script.src = "//dapi.kakao.com/v2/maps/sdk.js?appkey=426f46daef49480d78151c481bb7896a&autoload=false"
    script.async = true

    script.onload = () => {
      if (window.kakao && window.kakao.maps) {
        initializeMap()
      }
    }

    script.onerror = () => {
      console.error('Failed to load Kakao Maps SDK')
    }

    document.head.appendChild(script)

    function initializeMap() {
      try {
        window.kakao.maps.load(() => {
          if (mapRef.current) {
            const mapOption = {
              center: new window.kakao.maps.LatLng(37.5095, 127.0628),
              level: 7,
            }

            const kakaoMap = new window.kakao.maps.Map(mapRef.current, mapOption)
            setMap(kakaoMap)

            setTimeout(() => {
              setupMapBoundaries(kakaoMap)
            }, 100)
          }
        })
      } catch (error) {
        console.error('Error initializing map:', error)
      }
    }

    return () => {
      try {
        const existingScript = document.querySelector('script[src*="dapi.kakao.com"]')
        if (existingScript && document.head.contains(existingScript)) {
          document.head.removeChild(existingScript)
        }
      } catch (error) {
        console.error('Error removing script:', error)
      }
    }
  }, [])

  const setupMapBoundaries = (kakaoMap: any) => {
    const newPolygons: any[] = []
    const newOverlays: any[] = []

    // 서비스 가능 지역 목록
    const serviceAreas = getAllDistrictNames()

    // 배경 폴리곤 생성 (서비스 제한 지역)
    const koreaBackground = [
      new window.kakao.maps.LatLng(38.7, 125.0),
      new window.kakao.maps.LatLng(38.7, 132.0),
      new window.kakao.maps.LatLng(33.0, 132.0),
      new window.kakao.maps.LatLng(33.0, 125.0),
    ]

    // 서비스 지역 홀 생성
    const holePaths: any[] = []
    serviceAreas.forEach((district) => {
      const coords = getDistrictCoordinatesNew(district)
      if (coords) {
        holePaths.push(coords.slice().reverse()) // 홀 생성을 위해 반시계방향
      }
    })

    // 배경 폴리곤 (홀 포함)
    const backgroundPolygon = new window.kakao.maps.Polygon({
      map: kakaoMap,
      path: [koreaBackground].concat(holePaths),
      strokeWeight: 0,
      strokeOpacity: 0,
      fillColor: "#6b7280",
      fillOpacity: 0.4,
    })

    // 각 서비스 지역별 경계 및 라벨 추가
    serviceAreas.forEach((district) => {
      const coords = getDistrictCoordinatesNew(district)
      const center = getDistrictCenterNew(district)

      if (!coords || !center) return

      // 지역 경계 폴리곤
      const polygon = new window.kakao.maps.Polygon({
        map: kakaoMap,
        path: coords,
        strokeWeight: 2,
        strokeColor: "#0d9488",
        strokeOpacity: 0.8,
        fillColor: "#0d9488",
        fillOpacity: 0.1,
      })

      newPolygons.push(polygon)

      // 지역 라벨 오버레이
      const content = `
        <div style="
          background: white; 
          padding: 10px; 
          border-radius: 8px; 
          box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
          text-align: center; 
          font-family: inherit; 
          min-width: 120px; 
          border: 2px solid #0d9488;
        ">
          <div style="font-weight: bold; margin-bottom: 5px; font-size: 14px; color: #0d9488;">
            ${district}
          </div>
          <div style="
            padding: 4px 8px; 
            border-radius: 12px; 
            font-size: 12px; 
            background: #0d9488; 
            color: white; 
            font-weight: bold;
          ">
            ✓ 서비스 이용 가능
          </div>
        </div>
      `

      const overlay = new window.kakao.maps.CustomOverlay({
        content: content,
        position: center,
        yAnchor: 1,
      })

      newOverlays.push(overlay)

      // 폴리곤 클릭 이벤트
      try {
        window.kakao.maps.event.addListener(polygon, "click", () => {
          // 오버레이 토글
          if (overlay.getMap()) {
            overlay.setMap(null)
          } else {
            // 다른 오버레이들 숨기기
            newOverlays.forEach((ov) => ov.setMap(null))
            overlay.setMap(kakaoMap)
          }
        })

        // 호버 효과
        window.kakao.maps.event.addListener(polygon, "mouseover", () => {
          polygon.setOptions({
            strokeWeight: 3,
            strokeColor: "#0d9488",
            strokeOpacity: 1,
          })
        })

        window.kakao.maps.event.addListener(polygon, "mouseout", () => {
          polygon.setOptions({
            strokeWeight: 2,
            strokeColor: "#0d9488",
            strokeOpacity: 0.8,
          })
        })
      } catch (error) {
        console.error('Error adding polygon event listeners:', error)
      }
    })

    // 지도 클릭 시 오버레이 숨기기
    try {
      window.kakao.maps.event.addListener(kakaoMap, "click", () => {
        newOverlays.forEach((overlay) => overlay.setMap(null))
      })
    } catch (error) {
      console.error('Error adding map click listener:', error)
    }

    setPolygons(newPolygons)
  }

  // Update clusters when properties or zoom changes - optimized with useMemo
  // 지도 클러스터링은 viewport 내의 properties 사용
  const clusters = useMemo(() => {
    if (properties.length > 0) {
      console.log('Properties loaded:', properties.length)
      console.log('Sample properties:', properties.slice(0, 3).map(p => ({ 구: p.구, 동: p.동 })))
      const newClusters = clusterProperties(properties, currentZoom, transactionFilter)
      console.log('Clusters created:', newClusters.length)
      console.log('Cluster details:', newClusters.map(c => ({
        name: c.districtName || c.dongName,
        count: c.count,
        level: c.clusterLevel
      })))
      return newClusters
    }
    // Return empty array if no properties in viewport
    return []
  }, [properties, currentZoom, transactionFilter])

  const setupPropertyMarkers = (kakaoMap: any) => {
    // Clear existing markers efficiently
    markers.forEach(marker => {
      try {
        marker.setMap(null)
      } catch (error) {
        console.error('Error removing marker:', error)
      }
    })

    const newMarkers: any[] = []

    // Limit maximum markers to prevent performance issues
    const MAX_MARKERS = 500
    const clustersToRender = clusters.slice(0, MAX_MARKERS)

    if (clusters.length > MAX_MARKERS) {
      console.log(`Rendering ${MAX_MARKERS} out of ${clusters.length} clusters for performance`)
    }

    clustersToRender.forEach((cluster) => {
      try {
        const style = getClusterStyle(cluster.count, currentZoom, cluster.averagePrice)
        const position = new window.kakao.maps.LatLng(cluster.center.lat, cluster.center.lng)

        // Create enhanced marker content
        let markerContent = ''
        if (cluster.count === 1 && style.showDetails) {
          // Show detailed property information for single properties at high zoom
          markerContent = createDetailedMarkerContent(cluster.properties[0])
        } else if (cluster.count === 1) {
          // Naver-style property marker with transaction type indicator
          const property = cluster.properties[0]
          const isOffice = property.type === 'office' || property.name?.includes('오피스')

          // Get price info and determine transaction type (use raw values for accuracy)
          const saleHigh = property.매매_최고가;
          const rentHigh = property.전세_최고가;
          const monthlyHigh = property.월세_최고가;

          let priceText = '';
          let markerColor = '#3182f6'; // Default blue
          let iconText = '';

          // Helper to check if price is valid
          const isValidPrice = (price: any) => price && price !== '' && price !== '0' && parseFloat(price) > 0;

          // Determine transaction type based on active filter or priority
          // If transaction filter is active, show that type. Otherwise show by priority (매매 > 전세 > 월세)
          if (transactionFilter === "매매" && isValidPrice(saleHigh)) {
            const price = parseFloat(saleHigh) / 10000; // Convert 만원 to 억원
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            markerColor = '#EF4444'; // Vibrant red for sale
            iconText = '매';
          } else if (transactionFilter === "전세" && isValidPrice(rentHigh)) {
            const price = parseFloat(rentHigh) / 10000; // Convert 만원 to 억원
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            markerColor = '#3B82F6'; // Bright blue for jeonse
            iconText = '전';
          } else if (transactionFilter === "월세" && isValidPrice(monthlyHigh)) {
            const price = parseFloat(monthlyHigh); // Already in 만원
            if (price >= 10000) {
              const eok = price / 10000
              priceText = eok % 1 === 0 ? `${Math.round(eok)}억` : `${eok.toFixed(1)}억`
            } else {
              priceText = `${Math.round(price)}만`;
            }
            markerColor = '#10B981'; // Fresh green for monthly
            iconText = '월';
          } else if (isValidPrice(saleHigh)) {
            // Default priority: 매매
            const price = parseFloat(saleHigh) / 10000;
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            markerColor = '#EF4444';
            iconText = '매';
          } else if (isValidPrice(rentHigh)) {
            // Default priority: 전세
            const price = parseFloat(rentHigh) / 10000;
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            markerColor = '#3B82F6';
            iconText = '전';
          } else if (isValidPrice(monthlyHigh)) {
            // Default priority: 월세
            const price = parseFloat(monthlyHigh);
            if (price >= 10000) {
              const eok = price / 10000
              priceText = eok % 1 === 0 ? `${Math.round(eok)}억` : `${eok.toFixed(1)}억`
            } else {
              priceText = `${Math.round(price)}만`;
            }
            markerColor = '#10B981';
            iconText = '월';
          } else {
            priceText = '-';
            iconText = '?';
          }

          markerContent = `
            <div style="
              display: flex;
              flex-direction: column;
              align-items: center;
              cursor: pointer;
              position: relative;
            ">
              <!-- House icon with transaction type badge -->
              <div style="
                position: relative;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                <!-- House SVG -->
                <svg width="32" height="32" viewBox="0 0 32 32" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">
                  <!-- House body -->
                  <path d="M16 4 L4 14 L4 28 L28 28 L28 14 Z" fill="${markerColor}" stroke="white" stroke-width="1.5"/>
                  <!-- Door -->
                  <rect x="12" y="20" width="8" height="8" fill="white" opacity="0.9"/>
                  <!-- Roof -->
                  <path d="M16 2 L2 13 L4 13 L16 4 L28 13 L30 13 Z" fill="${markerColor}" stroke="white" stroke-width="1"/>
                </svg>

                <!-- Transaction type badge -->
                <div style="
                  position: absolute;
                  top: -4px;
                  right: -4px;
                  background: white;
                  color: ${markerColor};
                  border: 2px solid ${markerColor};
                  border-radius: 50%;
                  width: 16px;
                  height: 16px;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  font-size: 9px;
                  font-weight: 900;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                ">
                  ${iconText}
                </div>
              </div>

              <!-- Price label -->
              <div style="
                background: ${markerColor};
                color: white;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
                margin-top: 2px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                white-space: nowrap;
                border: 1px solid rgba(255,255,255,0.3);
              ">
                ${priceText}
              </div>
            </div>
          `
        } else {
          // Cluster marker
          markerContent = createClusterMarkerContent(cluster, style, transactionFilter)
        }

        // Create DOM element
        const markerDiv = document.createElement('div')
        markerDiv.innerHTML = markerContent
        const markerElement = markerDiv.firstElementChild as HTMLElement

        if (!markerElement) {
          console.error('Failed to create marker element')
          return
        }

        const marker = new window.kakao.maps.CustomOverlay({
          content: markerElement,
          position: position,
          yAnchor: 1,
        })

        marker.setMap(kakaoMap)
        newMarkers.push(marker)

        // Add interaction events
        if (markerElement.addEventListener) {
          markerElement.addEventListener('mouseenter', () => {
            markerElement.style.transform = 'scale(1.1)'
            markerElement.style.zIndex = '1000'
          })

          markerElement.addEventListener('mouseleave', () => {
            markerElement.style.transform = 'scale(1)'
            markerElement.style.zIndex = 'auto'
          })

          markerElement.addEventListener('click', () => {
            if (cluster.count === 1) {
              const property = cluster.properties[0] as unknown as PropertyData
              setSelectedProperty(property)
              kakaoMap.setCenter(position)
            } else {
              // Zoom in to cluster or show cluster properties
              kakaoMap.setCenter(position)
              kakaoMap.setLevel(Math.max(1, currentZoom - 2))
            }
          })
        }

      } catch (error) {
        console.error('Error creating marker:', error)
      }
    })

    setMarkers(newMarkers)
  }

  const showAllAreas = () => {
    if (map) {
      map.setCenter(new window.kakao.maps.LatLng(37.5095, 127.0628))
      map.setLevel(8)
    }
  }

  const showServiceAreas = () => {
    if (map) {
      map.setCenter(new window.kakao.maps.LatLng(37.5095, 127.0628))
      map.setLevel(6)
    }
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  // Setup zoom change listener with debouncing for performance
  useEffect(() => {
    if (!map || typeof window === 'undefined') return

    let timeoutId: NodeJS.Timeout | null = null

    const zoomChangeListener = () => {
      try {
        // Debounce zoom changes to reduce re-renders
        if (timeoutId) {
          clearTimeout(timeoutId)
        }

        timeoutId = setTimeout(() => {
          const level = map.getLevel()
          const prevZoom = currentZoom
          setCurrentZoom(level)

          // Reload properties only when crossing the level 6 boundary
          // or when in level < 6 (viewport mode)
          if ((prevZoom < 6 && level < 6) || (prevZoom < 6 && level >= 6) || (prevZoom >= 6 && level < 6)) {
            loadPropertiesFromAPI(map)
          }
        }, 150) // Wait 150ms after zoom stops
      } catch (error) {
        console.error('Error getting map level:', error)
      }
    }

    try {
      window.kakao.maps.event.addListener(map, "zoom_changed", zoomChangeListener)

      return () => {
        try {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          window.kakao.maps.event.removeListener(map, "zoom_changed", zoomChangeListener)
        } catch (error) {
          console.error('Error removing zoom listener:', error)
        }
      }
    } catch (error) {
      console.error('Error adding zoom listener:', error)
    }
  }, [map, loadPropertiesFromAPI])

  // Setup drag/move listener to reload properties when map viewport changes
  useEffect(() => {
    if (!map || typeof window === 'undefined') return

    let timeoutId: NodeJS.Timeout | null = null

    const dragEndListener = () => {
      try {
        // Debounce drag events to reduce API calls
        if (timeoutId) {
          clearTimeout(timeoutId)
        }

        timeoutId = setTimeout(() => {
          // 줌 레벨 6 이상일 때는 전역 데이터를 사용하므로 드래그 시 reload 안 함
          const currentLevel = map.getLevel()
          if (currentLevel < 6) {
            // 줌 레벨 5 이하일 때만 viewport 기반 reload
            loadPropertiesFromAPI(map)
          }
        }, 300) // Wait 300ms after drag stops
      } catch (error) {
        console.error('Error on drag end:', error)
      }
    }

    try {
      window.kakao.maps.event.addListener(map, "dragend", dragEndListener)

      return () => {
        try {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          window.kakao.maps.event.removeListener(map, "dragend", dragEndListener)
        } catch (error) {
          console.error('Error removing drag listener:', error)
        }
      }
    } catch (error) {
      console.error('Error adding drag listener:', error)
    }
  }, [map, loadPropertiesFromAPI])

  // Setup markers when clusters or transaction filter changes - with throttling
  useEffect(() => {
    if (!map) return

    // Use requestAnimationFrame for smoother updates
    let rafId: number | null = null

    const updateMarkers = () => {
      setupPropertyMarkers(map)
    }

    // Throttle marker updates to prevent excessive rendering
    rafId = requestAnimationFrame(updateMarkers)

    return () => {
      if (rafId) {
        cancelAnimationFrame(rafId)
      }
    }
  }, [map, clusters, transactionFilter])

  // Resize map when sidebar is toggled
  useEffect(() => {
    if (map) {
      // Wait for CSS transition to complete (300ms is typical)
      setTimeout(() => {
        try {
          map.relayout()
        } catch (error) {
          console.error('Error relayout map:', error)
        }
      }, 350)
    }
  }, [sidebarOpen, map])

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
                {selectedProperty ? selectedProperty.단지명 : "서울 강남3구 부동산 정보"}
              </h2>
              <p className="text-sm text-primary-foreground/80">
                {selectedProperty
                  ? `${selectedProperty.구} ${selectedProperty.동}`
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
                <SelectItem value="전체">전체 구</SelectItem>
                {serviceAreas.map((area) => (
                  <SelectItem key={area} value={area}>
                    {area}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="flex-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="이름순">이름순</SelectItem>
                <SelectItem value="가격순">가격순</SelectItem>
                <SelectItem value="신뢰도순">신뢰도순</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Badge variant="secondary" className="bg-primary text-primary-foreground">
              서비스 가능 지역
            </Badge>
            <Badge variant="outline">매물 클러스터</Badge>
          </div>
        </div>
        )}

        {/* Property List - Hide when showing property detail */}
        {!selectedProperty && (
        <div className="flex-1 overflow-y-auto" onScroll={handleScroll}>
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">매물 정보</h3>
              <span className="text-sm text-muted-foreground">총 {filteredProperties.length}개 매물</span>
            </div>

            {loading ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <div className="space-y-3">
                {displayedProperties.map((property, index) => {
                  // Display price based on active transaction filter
                  let primaryPrice = 'N/A'
                  let priceType = ''

                  if (transactionFilter === "매매" && property.매매_최저가_억원) {
                    primaryPrice = `${property.매매_최저가_억원}억`
                    priceType = '매매'
                  } else if (transactionFilter === "전세" && property.전세_최저가_억원) {
                    primaryPrice = `${property.전세_최저가_억원}억`
                    priceType = '전세'
                  } else if (transactionFilter === "월세" && property.월세_최저가) {
                    // Use raw value in 만원 units
                    primaryPrice = formatMonthlyPrice(parseFloat(property.월세_최저가))
                    priceType = '월세'
                  } else {
                    // Default priority when filter is "전체"
                    if (property.매매_최저가_억원) {
                      primaryPrice = `${property.매매_최저가_억원}억`
                      priceType = '매매'
                    } else if (property.전세_최저가_억원) {
                      primaryPrice = `${property.전세_최저가_억원}억`
                      priceType = '전세'
                    } else if (property.월세_최저가) {
                      // Use raw value in 만원 units
                      primaryPrice = formatMonthlyPrice(parseFloat(property.월세_최저가))
                      priceType = '월세'
                    } else {
                      primaryPrice = 'N/A'
                    }
                  }

                  const transactions = Number(property.총_거래건수) || 0

                  return (
                    <Card
                      key={`${property.단지명}-${index}`}
                      className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                        selectedProperty?.단지명 === property.단지명 ? "ring-2 ring-primary" : ""
                      }`}
                      onClick={() => handlePropertyClick(property)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium text-sm">{property.단지명}</h4>
                          <div className="flex items-center gap-1">
                            <div className={`w-2 h-2 rounded-full ${transactions > 50 ? 'bg-green-500' : transactions > 20 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                            <span className="text-xs text-muted-foreground">{transactions}</span>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">
                          {property.구} {property.동} | {property.단지요약}
                        </p>
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-sm font-medium">{primaryPrice}</span>
                            {priceType && <span className="text-xs text-muted-foreground ml-1">({priceType})</span>}
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {property.유형 || (property.type === 'office' ? '오피스텔' : '아파트')}
                          </Badge>
                        </div>
                        {property.면적요약 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {property.면적요약}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
                
                {isLoadingMore && (
                  <div className="flex items-center justify-center p-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
                    <span className="text-sm text-muted-foreground">더 많은 매물 로딩 중...</span>
                  </div>
                )}
                
                {itemsToShow >= filteredProperties.length && filteredProperties.length > 20 && (
                  <div className="text-center text-sm text-muted-foreground p-4 border-t">
                    모든 매물을 표시했습니다 ({filteredProperties.length}개)
                  </div>
                )}
                
                {itemsToShow < filteredProperties.length && !isLoadingMore && (
                  <div className="text-center text-sm text-muted-foreground p-4">
                    {filteredProperties.length - itemsToShow}개 매물 더 있음 (스크롤해서 더 보기)
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        )}

        {/* Property Detail - Show when property is selected */}
        {selectedProperty && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Price Information */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">가격 정보</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {selectedProperty.매매_최저가_억원 && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">매매</span>
                    <div className="text-right">
                      <span className="font-medium text-green-600">
                        {selectedProperty.매매_최저가_억원}억
                      </span>
                      {selectedProperty.매매_최고가_억원 && (
                        <span className="font-medium text-green-600">
                          {` ~ ${selectedProperty.매매_최고가_억원}억`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                {selectedProperty.전세_최저가_억원 && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">전세</span>
                    <div className="text-right">
                      <span className="font-medium text-blue-600">
                        {selectedProperty.전세_최저가_억원}억
                      </span>
                      {selectedProperty.전세_최고가_억원 && (
                        <span className="font-medium text-blue-600">
                          {` ~ ${selectedProperty.전세_최고가_억원}억`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                {selectedProperty.월세_최저가 && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">월세</span>
                    <div className="text-right">
                      <span className="font-medium text-orange-600">
                        {formatMonthlyPrice(parseFloat(selectedProperty.월세_최저가))}
                      </span>
                      {selectedProperty.월세_최고가 && (
                        <span className="font-medium text-orange-600">
                          {` ~ ${formatMonthlyPrice(parseFloat(selectedProperty.월세_최고가))}`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Property Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">단지 정보</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">면적</span>
                  <span className="font-medium">{selectedProperty.면적요약 || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">세대수</span>
                  <span className="font-medium">{selectedProperty.세대수}세대</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">동수</span>
                  <span className="font-medium">{selectedProperty.동수}개동</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">준공년월</span>
                  <span className="font-medium">{selectedProperty.준공년월}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">유형</span>
                  <Badge variant="outline">
                    {selectedProperty.유형 || (selectedProperty.type === 'office' ? '오피스텔' : '아파트')}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Transaction Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">거래 정보</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">총 거래건수</span>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${Number(selectedProperty.총_거래건수) > 50 ? 'bg-green-500' : Number(selectedProperty.총_거래건수) > 20 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                    <span className="font-medium">{selectedProperty.총_거래건수}건</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Summary */}
            {selectedProperty.단지요약 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">단지 요약</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {selectedProperty.단지요약}
                  </p>
                </CardContent>
              </Card>
            )}
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

          {/* Map Filter Controls - Naver Style */}
          <div className="absolute top-4 left-4 z-10 flex gap-2">
            {/* Property Type Filter */}
            <Select value={propertyTypeFilter} onValueChange={setPropertyTypeFilter}>
              <SelectTrigger className="w-[240px] bg-white shadow-md border-0 h-10 font-medium">
                <SelectValue placeholder="아파트, 오피스텔, 빌라, 단독/다가구, 원룸" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="전체">전체 유형</SelectItem>
                <SelectItem value="아파트">아파트</SelectItem>
                <SelectItem value="오피스텔">오피스텔</SelectItem>
                <SelectItem value="빌라">빌라</SelectItem>
                <SelectItem value="단독/다가구">단독/다가구</SelectItem>
                <SelectItem value="원룸">원룸</SelectItem>
              </SelectContent>
            </Select>

            {/* Transaction Type Filter */}
            <Select value={transactionFilter} onValueChange={setTransactionFilter}>
              <SelectTrigger className="w-[140px] bg-white shadow-md border-0 h-10 font-medium">
                <SelectValue placeholder="매매, 전세, 월세" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="전체">매매, 전세, 월세</SelectItem>
                <SelectItem value="매매">매매</SelectItem>
                <SelectItem value="전세">전세</SelectItem>
                <SelectItem value="월세">월세</SelectItem>
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
                면적 {selectedPyeongFilter && `${selectedPyeongFilter}`}
              </Button>

              {areaFilterOpen && (
                <div className="absolute top-full left-0 mt-2 w-[400px] bg-white shadow-lg rounded-lg border p-4 z-20">
                  <div className="space-y-6">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-medium">평형</span>
                        <span className="text-sm text-muted-foreground">
                          {areaRange[0]}평 ~ {areaRange[1] >= 70 ? '70평~' : `${areaRange[1]}평`}
                        </span>
                      </div>
                      <Slider
                        value={areaRange}
                        onValueChange={(value) => setAreaRange(value as [number, number])}
                        max={70}
                        step={5}
                        className="mb-4"
                      />

                      {/* Quick Select Buttons */}
                      <div className="grid grid-cols-4 gap-2 mb-2">
                        {['~10평', '10평대', '20평대', '30평대', '40평대', '50평대', '60평대', '70평~'].map((label) => (
                          <Button
                            key={label}
                            variant={selectedPyeongFilter === label ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => {
                              setSelectedPyeongFilter(label === selectedPyeongFilter ? null : label)
                              if (label === '~10평') setAreaRange([0, 10])
                              else if (label === '10평대') setAreaRange([10, 20])
                              else if (label === '20평대') setAreaRange([20, 30])
                              else if (label === '30평대') setAreaRange([30, 40])
                              else if (label === '40평대') setAreaRange([40, 50])
                              else if (label === '50평대') setAreaRange([50, 60])
                              else if (label === '60평대') setAreaRange([60, 70])
                              else if (label === '70평~') setAreaRange([70, 70])
                            }}
                            className="text-xs"
                          >
                            {label}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" onClick={() => {
                        setAreaRange([0, 70])
                        setSelectedPyeongFilter(null)
                      }}>
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

          {/* Map View Controls */}
          <div className="absolute top-4 right-4 z-10">
            <div className="bg-white rounded-lg shadow-md p-2 border-0">
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="px-3 py-2 h-8 hover:bg-muted text-xs"
                  onClick={showAllAreas}
                >
                  전체 보기
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="px-3 py-2 h-8 hover:bg-muted text-xs"
                  onClick={showServiceAreas}
                >
                  서비스 지역
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="px-3 py-2 h-8 hover:bg-muted text-xs"
                  onClick={toggleFullscreen}
                >
                  <span className="flex items-center gap-1">
                    {isFullscreen ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                    {isFullscreen ? "축소" : "확대"}
                  </span>
                </Button>
              </div>
            </div>
          </div>

          {/* Map Legend */}
          <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg">
            <h4 className="font-medium text-sm mb-2">범례</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-primary rounded-full"></div>
                <span>서비스 가능 지역</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-secondary rounded-full"></div>
                <span>부동산 매물</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-muted rounded-full"></div>
                <span>서비스 제한 지역</span>
              </div>
            </div>

            {loading && (
              <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-lg font-medium">부동산 데이터 로딩 중...</p>
                  <p className="text-sm text-muted-foreground">잠시만 기다려주세요</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    <FloatingChatButton />
    </>
  )
}
