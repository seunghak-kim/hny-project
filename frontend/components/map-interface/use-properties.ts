"use client"

import { useState, useEffect, useMemo, useCallback } from "react"
import type { PropertyData } from "./types"
import { parsePrice, isPriceInRange } from "./price-utils"

interface UsePropertiesProps {
  map: any
  propertyTypeFilter: string
  transactionFilter: string
  searchQuery: string
  filterType: string
  salePriceRange: [number, number]
  jeonsePriceRange: [number, number]
  monthlyPriceRange: [number, number]
  areaRange: [number, number]
  sortBy: string
}

export interface UsePropertiesReturn {
  properties: PropertyData[]  // 지도 렌더링용 (viewport 기반)
  allProperties: PropertyData[]  // 사이드바 검색용 (전체 매물)
  filteredProperties: PropertyData[]  // 필터링된 매물 (사이드바 표시용)
  displayedProperties: PropertyData[]  // 무한 스크롤용 (실제 표시되는 매물)
  loading: boolean
  isLoadingMore: boolean
  loadPropertiesFromAPI: (mapInstance: any) => Promise<void>
  handlePropertyClick: (property: PropertyData) => Promise<void>
  handleScroll: (e: React.UIEvent<HTMLDivElement>) => void
  transformAPIResponse: (data: any[]) => PropertyData[]
  selectedProperty: PropertyData | null
  setSelectedProperty: React.Dispatch<React.SetStateAction<PropertyData | null>>
}

/**
 * Custom hook for property data management, API loading, and filtering
 */
export function useProperties(props: UsePropertiesProps): UsePropertiesReturn {
  const {
    map,
    propertyTypeFilter,
    transactionFilter,
    searchQuery,
    filterType,
    salePriceRange,
    jeonsePriceRange,
    monthlyPriceRange,
    areaRange,
    sortBy
  } = props

  const [properties, setProperties] = useState<PropertyData[]>([])  // 지도 렌더링용
  const [allProperties, setAllProperties] = useState<PropertyData[]>([])  // 사이드바 검색용
  const [displayedProperties, setDisplayedProperties] = useState<PropertyData[]>([])
  const [itemsToShow, setItemsToShow] = useState(20)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedProperty, setSelectedProperty] = useState<PropertyData | null>(null)

  // Transform API response to PropertyData format (공통 함수)
  const transformAPIResponse = useCallback((data: any[]): PropertyData[] => {
    console.log('[Transform] Total items received:', data.length)
    console.log('[Transform] First 3 items:', data.slice(0, 3))

    const filtered = data.filter((item: any) => {
      // 동/구 단위 집계 데이터는 별도 검증 후 통과
      if (item.type === "dong" || item.type === "gu") {
        console.log('[Transform] Found aggregate data:', item.type, item)

        // 집계 데이터는 avg_*_price_eok 필드로 가격 검증
        const hasAggregatePrice = item.avg_sale_price_eok ||
          item.avg_jeonse_price_eok ||
          item.avg_rent_price_eok;

        if (!hasAggregatePrice) {
          console.warn('[Transform] Aggregate data has no prices:', item)
          return false
        }

        return true
      }

      // 클러스터 데이터는 스킵 (지도에 표시하지 않음)
      if (item.type === "cluster") {
        console.log('[Transform] Skipping cluster data')
        return false
      }

      // 개별 매물: 위도/경도 체크
      const hasCoords = item.latitude && item.longitude
      if (!hasCoords) {
        console.warn('[Transform] No coordinates:', item.name)
        return false
      }

      // 개별 매물: 가격 체크
      const hasSalePrice = item.sale_max_price && item.sale_max_price > 0
      const hasJeonsePrice = item.jeonse_max_price && item.jeonse_max_price > 0
      const hasMonthlyPrice = item.rent_max_price && item.rent_max_price > 0

      const hasAnyPrice = hasSalePrice || hasJeonsePrice || hasMonthlyPrice
      if (!hasAnyPrice) {
        console.warn('[Transform] No valid price:', item.name)
      }

      return hasAnyPrice
    })

    return filtered.map((item: any) => {
      // 동/구 집계 데이터 처리
      if (item.type === "dong" || item.type === "gu") {
        return {
          name: item.type === "gu" ? item.gu : `${item.gu} ${item.dong}`,
          gu: item.gu || "",
          dong: item.dong || "",
          latitude: item.latitude,
          longitude: item.longitude,
          summary: "",
          total_article_count: item.total_transactions?.toString() || item.count?.toString() || "0",
          area_summary: "",
          total_households: "",
          total_buildings: "",
          completion_date: "",
          // 집계 데이터는 avg_*_price_eok 필드를 사용 (이미 억원 단위 문자열)
          sale_min_price_eok: item.avg_sale_price_eok || "",
          sale_max_price_eok: item.avg_sale_price_eok || "",
          jeonse_min_price_eok: item.avg_jeonse_price_eok || "",
          jeonse_max_price_eok: item.avg_jeonse_price_eok || "",
          rent_min_price_eok: item.avg_rent_price_eok || "",
          rent_max_price_eok: item.avg_rent_price_eok || "",
          // Raw 가격 데이터는 없음 (집계된 데이터이므로)
          sale_min_price: "",
          sale_max_price: "",
          jeonse_min_price: "",
          jeonse_max_price: "",
          rent_min_price: "",
          rent_max_price: "",
          property_type: item.property_type || (item.type === "gu" ? "구 최저가" : "동 최저가"),
          type: item.type as any, // "dong" or "gu"
          count: item.count || 1  // 집계된 매물 개수
        }
      }

      // 개별 매물 데이터 처리
      return {
        name: item.name,
        gu: item.gu || "",
        dong: item.dong || "",
        latitude: item.latitude,
        longitude: item.longitude,
        summary: "",
        total_article_count: item.total_article_count?.toString() || "0",
        area_summary: item.area_summary || "",
        total_households: item.total_households?.toString() || "",
        total_buildings: item.total_buildings?.toString() || "",
        completion_date: item.completion_date || "",
        sale_min_price_eok: item.sale_min_price_eok || "",
        sale_max_price_eok: item.sale_max_price_eok || "",
        jeonse_min_price_eok: item.jeonse_min_price_eok || "",
        jeonse_max_price_eok: item.jeonse_max_price_eok || "",
        rent_min_price_eok: item.rent_min_price_eok || "",
        rent_max_price_eok: item.rent_max_price_eok || "",
        sale_min_price: item.sale_min_price?.toString() || "",
        sale_max_price: item.sale_max_price?.toString() || "",
        jeonse_min_price: item.jeonse_min_price?.toString() || "",
        jeonse_max_price: item.jeonse_max_price?.toString() || "",
        rent_min_price: item.rent_min_price?.toString() || "",
        rent_max_price: item.rent_max_price?.toString() || "",
        property_type: item.property_type || "아파트",
        type: "residential" as const,
        // 주변 시설 정보 추가
        nearby_subway_stations: item.nearby_subway_stations || undefined,
        nearby_schools: item.nearby_schools || undefined,
        nearby_marts: item.nearby_marts || undefined
      }
    })
  }, [])

  // Load ALL properties for sidebar search (전체 매물)
  const loadAllPropertiesFromAPI = useCallback(async () => {
    try {
      // 전체 매물을 가져오기 위해 서울 전체 범위 사용
      const params = new URLSearchParams({
        south: "37.4",
        north: "37.7",
        west: "126.8",
        east: "127.2",
        limit: "20000", // 전체 매물 로드 (사이드바 검색용)
      })

      // Add filters
      if (propertyTypeFilter !== "전체") {
        const typeMapping: { [key: string]: string } = {
          "아파트": "apartment",
          "오피스텔": "officetel",
          "빌라": "villa",
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
  }, [propertyTypeFilter, transactionFilter, transformAPIResponse])

  // Load property data from API based on map viewport (지도 렌더링용)
  const loadPropertiesFromAPI = useCallback(async (mapInstance: any) => {
    console.log('[useProperties] loadPropertiesFromAPI called', { mapInstance: !!mapInstance })
    if (!mapInstance) return

    try {
      setLoading(true)
      console.log('[useProperties] Loading started')

      // Get map bounds
      const bounds = mapInstance.getBounds()
      const swLatLng = bounds.getSouthWest()
      const neLatLng = bounds.getNorthEast()

      // Get current zoom level
      const zoom: number = mapInstance.getLevel()
      console.log('[API] Current zoom level:', zoom)

      let south = swLatLng.getLat()
      let north = neLatLng.getLat()
      let west = swLatLng.getLng()
      let east = neLatLng.getLng()

      // 줌 레벨 7 이상(축소)일 때, 보이는 영역보다 더 넓은 데이터를 요청하여 부드러운 경험 제공
      if (zoom >= 7) {
        const latExpansion = (north - south) * 0.5 // 50% 확장
        const lngExpansion = (east - west) * 0.5   // 50% 확장
        south -= latExpansion
        north += latExpansion
        west -= lngExpansion
        east += lngExpansion
      }

      // 항상 현재 viewport 기반으로 데이터 로드
      // 백엔드에서 zoom 레벨에 따라 자동으로 집계 레벨 결정
      const params = new URLSearchParams({
        south: south.toString(),
        north: north.toString(),
        west: west.toString(),
        east: east.toString(),
        zoom: zoom.toString(),
        limit: "5000",
      })

      // Add filters
      if (propertyTypeFilter !== "전체") {
        const typeMapping: { [key: string]: string } = {
          "아파트": "apartment",
          "오피스텔": "officetel",
          "빌라": "villa",
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

      console.log('[useProperties] Fetching properties with params:', params.toString())
      // Fetch from API
      const response = await fetch(`http://localhost:8000/api/real-estate/properties?${params}`)
      const data = await response.json()
      console.log('[useProperties] API response received, items:', data.length)

      const transformed = transformAPIResponse(data)
      console.log('[useProperties] Transformed items:', transformed.length)

      setProperties(transformed)
    } catch (error) {
      console.error("Error loading property data from API:", error)
      setProperties([])
    } finally {
      console.log('[useProperties] Loading finished')
      setLoading(false)
    }
  }, [propertyTypeFilter, transactionFilter, transformAPIResponse])

  // Load all properties for sidebar search (초기 로딩)
  useEffect(() => {
    loadAllPropertiesFromAPI()
  }, [loadAllPropertiesFromAPI])

  // Load properties when map is first created
  useEffect(() => {
    if (map) {
      loadPropertiesFromAPI(map)
    }
  }, [map, loadPropertiesFromAPI])

  // Reload properties when filters change
  useEffect(() => {
    if (map) {
      loadPropertiesFromAPI(map)
    }
    // Also reload all properties for sidebar
    loadAllPropertiesFromAPI()
  }, [propertyTypeFilter, transactionFilter, loadPropertiesFromAPI, loadAllPropertiesFromAPI])

  // Filter properties based on search and filters - optimized with useMemo
  // 사이드바 검색은 allProperties 사용 (전체 매물)
  const filteredProperties = useMemo(() => {
    let filtered = allProperties

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (property) =>
          property.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          property.gu.includes(searchQuery) ||
          property.dong.includes(searchQuery)
      )
    }

    // District filter
    if (filterType !== "전체") {
      filtered = filtered.filter((property) => property.gu === filterType)
    }

    // 가격이 0원인 매물 필터링
    filtered = filtered.filter((property) => {
      // 동/구 집계 데이터는 통과
      if (property.type === "dong" || property.type === "gu") {
        return true
      }

      // 개별 매물: 최소 하나의 가격이 0보다 커야 함
      const hasSale = parsePrice(property.sale_max_price) > 0
      const hasJeonse = parsePrice(property.jeonse_max_price) > 0
      const hasRent = parsePrice(property.rent_max_price) > 0

      return hasSale || hasJeonse || hasRent
    })

    // Property type filter
    if (propertyTypeFilter !== "전체") {
      filtered = filtered.filter((property) => {
        const propertyType = property.property_type || (property.type === 'office' ? '오피스텔' : '아파트')

        if (propertyTypeFilter === "아파트") {
          return propertyType === "아파트" || propertyType === "APT"
        } else if (propertyTypeFilter === "오피스텔") {
          return propertyType === "오피스텔" || propertyType === "OPST"
        } else if (propertyTypeFilter === "빌라") {
          return propertyType === "빌라" || propertyType.includes("빌라")
        } else if (propertyTypeFilter === "단독/다가구") {
          return propertyType === "단독/다가구" || propertyType.includes("단독") || propertyType.includes("다가구")
        }
        return true
      })
    }

    // Transaction type filter - use raw 만원 values
    if (transactionFilter !== "전체") {
      filtered = filtered.filter((property) => {
        if (transactionFilter === "매매") {
          return parsePrice(property.sale_max_price) > 0
        } else if (transactionFilter === "전세") {
          return parsePrice(property.jeonse_max_price) > 0
        } else if (transactionFilter === "월세") {
          return parsePrice(property.rent_max_price) > 0
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

        // Check each price type
        if (isPriceInRange(property.sale_max_price, salePriceRange[0], salePriceRange[1])) {
          matchesFilter = true
        }
        if (isPriceInRange(property.jeonse_max_price, jeonsePriceRange[0], jeonsePriceRange[1])) {
          matchesFilter = true
        }
        if (isPriceInRange(property.rent_max_price, monthlyPriceRange[0], monthlyPriceRange[1])) {
          matchesFilter = true
        }

        return matchesFilter
      })
    }

    // Area filter - only apply if not at default range
    const isAreaFilterActive = areaRange[0] > 0 || areaRange[1] < 70

    if (isAreaFilterActive) {
      filtered = filtered.filter((property) => {
        const areaStr = property.area_summary
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

    // Apply sorting
    if (sortBy === "이름순") {
      filtered.sort((a, b) => a.name.localeCompare(b.name))
    } else if (sortBy === "가격순") {
      filtered.sort((a, b) => {
        // Helper function to get price value for sorting
        const getPriceValue = (property: PropertyData): number => {
          // 거래 필터에 따라 해당 가격 반환
          if (transactionFilter === "매매") {
            const price = parsePrice(property.sale_max_price)
            return price > 0 ? price : Infinity
          } else if (transactionFilter === "전세") {
            const price = parsePrice(property.jeonse_max_price)
            return price > 0 ? price : Infinity
          } else if (transactionFilter === "월세") {
            const price = parsePrice(property.rent_max_price)
            return price > 0 ? price : Infinity
          } else {
            // "전체"인 경우 매매 > 전세 > 월세 우선순위로 가격 반환
            const salePrice = parsePrice(property.sale_max_price)
            if (salePrice > 0) return salePrice

            const jeonsePrice = parsePrice(property.jeonse_max_price)
            if (jeonsePrice > 0) return jeonsePrice

            const rentPrice = parsePrice(property.rent_max_price)
            if (rentPrice > 0) return rentPrice

            return Infinity // 가격 정보가 없는 경우 맨 뒤로
          }
        }

        const priceA = getPriceValue(a)
        const priceB = getPriceValue(b)
        return priceA - priceB // 오름차순 정렬 (낮은 가격부터)
      })
    }

    return filtered
  }, [allProperties, searchQuery, filterType, propertyTypeFilter, transactionFilter, salePriceRange, jeonsePriceRange, monthlyPriceRange, areaRange, sortBy])

  // Reset pagination when filters change
  useEffect(() => {
    setItemsToShow(20)
  }, [filteredProperties])

  // Update displayed properties when filteredProperties or itemsToShow changes
  useEffect(() => {
    setDisplayedProperties(filteredProperties.slice(0, itemsToShow))
  }, [filteredProperties, itemsToShow])

  // Infinite scroll handler
  const loadMoreProperties = useCallback(() => {
    if (isLoadingMore || itemsToShow >= filteredProperties.length) return

    setIsLoadingMore(true)
    setTimeout(() => {
      setItemsToShow(prev => Math.min(prev + 20, filteredProperties.length))
      setIsLoadingMore(false)
    }, 500)
  }, [isLoadingMore, itemsToShow, filteredProperties.length])

  // Scroll event handler
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget

    if (scrollHeight - scrollTop <= clientHeight + 100) {
      loadMoreProperties()
    }
  }, [loadMoreProperties])

  // Handle property click with detailed info fetching
  const handlePropertyClick = useCallback(async (property: PropertyData) => {
    // If property doesn't have nearby facilities, fetch detailed info
    if (!property.nearby_subway_stations && !property.nearby_schools && !property.nearby_marts && property.latitude && property.longitude) {
      try {
        // Fetch detailed property info with nearby facilities (small area, limit=1)
        const smallRange = 0.001 // ~100m
        const params = new URLSearchParams({
          south: (property.latitude - smallRange).toString(),
          north: (property.latitude + smallRange).toString(),
          west: (property.longitude - smallRange).toString(),
          east: (property.longitude + smallRange).toString(),
          limit: "1",
          zoom: "1"
        })

        const response = await fetch(`http://localhost:8000/api/real-estate/properties?${params}`)
        const data = await response.json()

        if (data && data.length > 0) {
          // Use the detailed property data with nearby facilities
          const detailedProperty = transformAPIResponse(data)[0]
          setSelectedProperty(detailedProperty)
        } else {
          setSelectedProperty(property)
        }
      } catch (error) {
        console.error("Error fetching property details:", error)
        setSelectedProperty(property)
      }
    } else {
      setSelectedProperty(property)
    }

    // Center map on selected property and zoom to level 1 (20m)
    if (map && property.latitude && property.longitude) {
      const position = new window.kakao.maps.LatLng(property.latitude, property.longitude)
      map.setCenter(position)
      map.setLevel(1) // 줌 레벨 1 (20m)
    }
  }, [map, transformAPIResponse])

  return {
    properties,
    allProperties,
    filteredProperties,
    displayedProperties,
    loading,
    isLoadingMore,
    loadPropertiesFromAPI,
    handlePropertyClick,
    handleScroll,
    transformAPIResponse,
    selectedProperty,
    setSelectedProperty
  }
}
