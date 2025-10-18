"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, MapPin, Maximize2, Minimize2 } from "lucide-react"
import { getDistrictCoordinatesNew, getDistrictCenterNew, getAllDistrictNames } from "@/lib/district-coordinates"
import { clusterProperties, getClusterStyle, createDetailedMarkerContent, createClusterMarkerContent, type Cluster } from "@/lib/clustering"

declare global {
  interface Window {
    kakao: any
  }
}

interface PropertyData {
  단지명: string
  구: string
  동: string
  매매_최저가_억원?: string
  매매_최고가_억원?: string
  전세_최저가_억원?: string
  전세_최고가_억원?: string
  월세_최저가_억원?: string
  월세_최고가_억원?: string
  단지요약: string
  총_거래건수: string
  면적요약: string
  세대수: string
  동수: string
  준공년월: string
  위도?: number
  경도?: number
  type?: "office" | "residential"
}

export function MapInterface() {
  const mapRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<any>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedProperty, setSelectedProperty] = useState<PropertyData | null>(null)
  const [filterType, setFilterType] = useState<string>("전체")
  const [sortBy, setSortBy] = useState<string>("이름순")
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [markers, setMarkers] = useState<any[]>([])
  const [polygons, setPolygons] = useState<any[]>([])
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [currentZoom, setCurrentZoom] = useState(7)
  const [properties, setProperties] = useState<PropertyData[]>([])
  const [filteredProperties, setFilteredProperties] = useState<PropertyData[]>([])
  const [loading, setLoading] = useState(true)
  const [displayedProperties, setDisplayedProperties] = useState<PropertyData[]>([])
  const [itemsToShow, setItemsToShow] = useState(20)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // 서비스 가능 지역 목록
  const serviceAreas = getAllDistrictNames()

  // Load CSV data
  useEffect(() => {
    const loadPropertyData = async () => {
      try {
        setLoading(true)

        // Load real estate data with coordinates
        const response = await fetch("/data/real_estate_with_coordinates_kakao.csv")
        const csvText = await response.text()

        // Parse CSV data with proper handling of quoted values
        const parseCSV = (text: string): PropertyData[] => {
          const lines = text.split("\n")
          
          // Optimized CSV line parser
          const parseCSVLine = (line: string): string[] => {
            const result: string[] = []
            let current = ""
            let inQuotes = false
            
            for (let i = 0; i < line.length; i++) {
              const char = line[i]
              
              if (char === '"') {
                inQuotes = !inQuotes
              } else if (char === ',' && !inQuotes) {
                result.push(current)
                current = ""
              } else {
                current += char
              }
            }
            result.push(current)
            return result
          }

          const headers = parseCSVLine(lines[0])

          return lines
            .slice(1)
            .filter((line) => line.trim())
            .map((line) => {
              const values = parseCSVLine(line)
              const obj: any = { type: "residential" }
              
              // Only process essential fields for performance
              const essentialFields = ['단지명', '구', '동', '위도', '경도', '단지요약', '총_거래건수', '면적요약', '세대수', '동수', '준공년월', '매매_최저가_억원', '매매_최고가_억원', '전세_최저가_억원', '전세_최고가_억원', '월세_최저가_억원', '월세_최고가_억원']
              
              headers.forEach((header, index) => {
                const cleanHeader = header.replace(/^\uFEFF/, '').trim()
                if (essentialFields.includes(cleanHeader) && values[index]) {
                  obj[cleanHeader] = values[index].trim()
                }
              })
              
              // Parse coordinates as numbers
              if (obj.위도) obj.위도 = parseFloat(obj.위도)
              if (obj.경도) obj.경도 = parseFloat(obj.경도)
              
              return obj as PropertyData
            })
        }

        const allProperties = parseCSV(csvText)
        setProperties(allProperties)
        setFilteredProperties(allProperties)
      } catch (error) {
        console.error("Error loading property data:", error)
      } finally {
        setLoading(false)
      }
    }

    loadPropertyData()
  }, [])

  // Filter properties based on search and filters
  useEffect(() => {
    let filtered = properties

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

    setFilteredProperties(filtered)
    setItemsToShow(20) // Reset pagination when filters change
  }, [properties, searchQuery, filterType])

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
    setSidebarOpen(true) // Show sidebar when property is clicked
  }

  const getTrustScoreColor = (score: number) => {
    if (score >= 90) return "bg-green-500"
    if (score >= 70) return "bg-yellow-500"
    return "bg-red-500"
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

  // Update clusters when properties or zoom changes
  useEffect(() => {
    if (filteredProperties.length > 0) {
      // console.log('Current zoom level:', currentZoom) // 디버깅용
      const newClusters = clusterProperties(filteredProperties, currentZoom)
      setClusters(newClusters)
      // console.log('Clusters created:', newClusters.length) // 디버깅용
    }
  }, [filteredProperties, currentZoom])

  const setupPropertyMarkers = (kakaoMap: any) => {
    // Clear existing markers
    markers.forEach(marker => {
      try {
        marker.setMap(null)
      } catch (error) {
        console.error('Error removing marker:', error)
      }
    })

    const newMarkers: any[] = []

    clusters.forEach((cluster) => {
      try {
        const style = getClusterStyle(cluster.count, currentZoom, cluster.averagePrice)
        const position = new window.kakao.maps.LatLng(cluster.center.lat, cluster.center.lng)

        // Create enhanced marker content
        let markerContent = ''
        if (cluster.count === 1 && style.showDetails) {
          // Show detailed property information for single properties at high zoom
          markerContent = createDetailedMarkerContent(cluster.properties[0])
        } else if (cluster.count === 1) {
          // Hogangnono-style house icon with price info
          const property = cluster.properties[0]
          const isOffice = property.type === 'office' || property.name?.includes('오피스')
          
          // Get price info
          const saleHigh = property.매매_최고가_억원;
          const saleLow = property.매매_최저가_억원;
          const rentHigh = property.전세_최고가_억원;
          const rentLow = property.전세_최저가_억원;
          
          let priceText = '';
          let priceColor = '#2563eb'; // Default blue
          
          if (saleHigh && saleHigh !== '' && saleHigh !== '0') {
            const price = parseFloat(saleHigh);
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            // Price-based coloring
            if (price >= 50) priceColor = '#dc2626'; // Red for expensive
            else if (price >= 30) priceColor = '#f59e0b'; // Orange 
            else if (price >= 15) priceColor = '#10b981'; // Green
            else priceColor = '#3b82f6'; // Blue
          } else if (rentHigh && rentHigh !== '' && rentHigh !== '0') {
            const price = parseFloat(rentHigh);
            priceText = price >= 1 ? `${price.toFixed(0)}억` : `${(price * 10).toFixed(0)}천`;
            priceColor = '#8b5cf6'; // Purple for rent
          }
          
          markerContent = `
            <div style="
              background: ${priceColor};
              color: white;
              padding: 2px 6px;
              border-radius: 4px;
              border: 1px solid rgba(255,255,255,0.8);
              box-shadow: 0 2px 8px rgba(0,0,0,0.3);
              cursor: pointer;
              font-size: 10px;
              font-weight: 700;
              text-align: center;
              min-width: 35px;
              transition: all 0.2s ease;
              position: relative;
            ">
              ${priceText || '가격미상'}
              <div style="
                position: absolute;
                bottom: -4px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid ${priceColor};
              "></div>
            </div>
          `
        } else {
          // Cluster marker
          markerContent = createClusterMarkerContent(cluster, style)
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
              setSelectedProperty(cluster.properties[0] as unknown as PropertyData)
              setSidebarOpen(true) // Show sidebar when marker is clicked
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

  // Setup zoom change listener
  useEffect(() => {
    if (!map || typeof window === 'undefined') return

    const zoomChangeListener = () => {
      try {
        const level = map.getLevel()
        setCurrentZoom(level)
      } catch (error) {
        console.error('Error getting map level:', error)
      }
    }

    try {
      window.kakao.maps.event.addListener(map, "zoom_changed", zoomChangeListener)

      return () => {
        try {
          window.kakao.maps.event.removeListener(map, "zoom_changed", zoomChangeListener)
        } catch (error) {
          console.error('Error removing zoom listener:', error)
        }
      }
    } catch (error) {
      console.error('Error adding zoom listener:', error)
    }
  }, [map])

  // Setup markers when clusters change
  useEffect(() => {
    if (map && clusters.length > 0) {
      setupPropertyMarkers(map)
    }
  }, [map, clusters])

  return (
    <div className={`${isFullscreen ? "fixed inset-0 z-50" : ""} flex h-full bg-background`}>
      {/* Left Panel - Search and Filters */}
      <div className="w-80 border-r border-border flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border bg-primary">
          <h2 className="text-lg font-bold text-primary-foreground">서울 강남3구 부동산 정보</h2>
          <p className="text-sm text-primary-foreground/80">서비스 가능 지역: 강남구, 서초구, 송파구</p>
        </div>

        {/* Search */}
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

        {/* Property List */}
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
                  const primaryPrice = property.매매_최저가_억원 || property.전세_최저가_억원 || property.월세_최저가_억원 || 'N/A'
                  const priceType = property.매매_최저가_억원 ? '매매' : property.전세_최저가_억원 ? '전세' : property.월세_최저가_억원 ? '월세' : ''
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
                            {property.type === 'office' ? '오피스텔' : '아파트'}
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
      </div>

      {/* Right Panel - Map */}
      <div className="flex-1 relative">
        <div className="w-full h-full relative overflow-hidden">
          <div ref={mapRef} className="w-full h-full" />

          {/* Map Controls */}
          <div className="absolute top-4 left-4 z-10">
            <div className="bg-white rounded-lg shadow-md p-2 border border-border">
              <div className="flex gap-1">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="px-3 py-2 h-8 hover:bg-muted"
                  onClick={showAllAreas}
                >
                  전체 보기
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="px-3 py-2 h-8 hover:bg-muted"
                  onClick={showServiceAreas}
                >
                  서비스 지역
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="px-3 py-2 h-8 hover:bg-muted"
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

        {/* Property Detail Sidebar */}
        {sidebarOpen && selectedProperty && (
          <div className="absolute inset-y-0 right-0 w-96 bg-background border-l border-border shadow-2xl z-50 flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border bg-primary">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-primary-foreground">{selectedProperty.단지명}</h3>
                  <div className="flex items-center gap-1 mt-1">
                    <MapPin className="h-3 w-3 text-primary-foreground/70" />
                    <span className="text-sm text-primary-foreground/70">{selectedProperty.구} {selectedProperty.동}</span>
                  </div>
                </div>
                <Button 
                  variant="ghost" 
                  size="icon"
                  className="text-primary-foreground hover:bg-primary-foreground/20"
                  onClick={() => setSidebarOpen(false)}
                >
                  ✕
                </Button>
              </div>
            </div>

            {/* Content */}
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
                          {selectedProperty.매매_최저가_억원}
                        </span>
                        {selectedProperty.매매_최고가_억원 && (
                          <span className="font-medium text-green-600">
                            {` ~ ${selectedProperty.매매_최고가_억원}`}
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
                          {selectedProperty.전세_최저가_억원}
                        </span>
                        {selectedProperty.전세_최고가_억원 && (
                          <span className="font-medium text-blue-600">
                            {` ~ ${selectedProperty.전세_최고가_억원}`}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {selectedProperty.월세_최저가_억원 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">월세</span>
                      <div className="text-right">
                        <span className="font-medium text-orange-600">
                          {selectedProperty.월세_최저가_억원}
                        </span>
                        {selectedProperty.월세_최고가_억원 && (
                          <span className="font-medium text-orange-600">
                            {` ~ ${selectedProperty.월세_최고가_억원}`}
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
                      {selectedProperty.type === 'office' ? '오피스텔' : '아파트'}
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
          </div>
        )}
      </div>
    </div>
  )
}
