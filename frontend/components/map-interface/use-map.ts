"use client"

import { useState, useEffect, useMemo, useCallback, useRef } from "react"
import { getAllDistrictNames, getDistrictCoordinatesNew, getDistrictCenterNew } from "@/lib/district-coordinates"
import { clusterProperties, getClusterStyle, createDetailedMarkerContent, createClusterMarkerContent } from "@/lib/clustering"
import type { PropertyData } from "./types"
import { createPropertyMarkerContent, calculateClusterAveragePrice } from "./marker-utils"

declare global {
  interface Window {
    kakao: any
  }
}

interface UseMapProps {
  mapRef: React.RefObject<HTMLDivElement>
  properties: PropertyData[]
  transactionFilter: string
  onPropertySelect: (property: PropertyData) => void
}

export interface UseMapReturn {
  map: any
  currentZoom: number
  loading: boolean
  clusters: any[]
}

/**
 * Custom hook for Kakao Map initialization, boundaries setup, and marker rendering
 */
export function useMap(props: UseMapProps): UseMapReturn {
  const { mapRef, properties, transactionFilter, onPropertySelect } = props

  const [map, setMap] = useState<any>(null)
  const markersRef = useRef<any[]>([])
  const polygonsRef = useRef<any[]>([])
  const [currentZoom, setCurrentZoom] = useState(7)
  const [loading, setLoading] = useState(true)

  // Setup map boundaries with service area polygons
  const setupMapBoundaries = useCallback((kakaoMap: any) => {
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

    polygonsRef.current = newPolygons
  }, [])

  // Initialize Kakao Map
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
            setLoading(false)

            // Setup zoom change listener
            window.kakao.maps.event.addListener(kakaoMap, "zoom_changed", () => {
              const level = kakaoMap.getLevel()
              setCurrentZoom(level)
            })

            setTimeout(() => {
              setupMapBoundaries(kakaoMap)
            }, 100)
          }
        })
      } catch (error) {
        console.error('Error initializing map:', error)
        setLoading(false)
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
  }, [mapRef, setupMapBoundaries])

  // Update clusters when properties or zoom changes - optimized with useMemo
  const clusters = useMemo(() => {
    console.log('[useMap] Recalculating clusters', {
      propertiesCount: properties.length,
      zoom: currentZoom,
      transactionFilter
    })

    // 줌 레벨 9 이상(축소 상태)에서는 아무것도 표시하지 않음
    if (currentZoom >= 9) {
      console.log('[useMap] Zoom too high, returning empty clusters')
      return []
    }

    if (properties.length > 0) {
      const newClusters = clusterProperties(properties, currentZoom, transactionFilter)
      console.log('[useMap] Clusters calculated:', newClusters.length)
      return newClusters
    }
    // Return empty array if no properties in viewport
    console.log('[useMap] No properties, returning empty clusters')
    return []
  }, [properties, currentZoom, transactionFilter])

  // Setup property markers using the new marker utilities
  const setupPropertyMarkers = useCallback((kakaoMap: any) => {
    console.log('[useMap] setupPropertyMarkers called', {
      clustersCount: clusters.length,
      zoom: currentZoom,
      markersCount: markersRef.current.length
    })

    // Clear existing markers efficiently
    markersRef.current.forEach(marker => {
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

    if (clusters.length === 0) {
      console.log('[useMap] No clusters to render')
      markersRef.current = []
      return
    }

    console.log('[useMap] Rendering clusters:', clustersToRender.length)

    clustersToRender.forEach((cluster, index) => {
      try {
        const style = getClusterStyle(cluster.count, currentZoom, cluster.averagePrice)
        const position = new window.kakao.maps.LatLng(cluster.center.lat, cluster.center.lng)

        // Create enhanced marker content
        let markerContent = ''
        if (cluster.count === 1 && style.showDetails) {
          // Show detailed property information for single properties at high zoom
          markerContent = createDetailedMarkerContent(cluster.properties[0])
        } else if (cluster.count === 1) {
          // Use new marker utility for single property
          const property = cluster.properties[0] as unknown as PropertyData
          markerContent = createPropertyMarkerContent(property, transactionFilter)
        } else {
          // Cluster marker
          const avgPrice = calculateClusterAveragePrice(
            cluster.properties as unknown as PropertyData[],
            transactionFilter
          )
          const tempCluster = { ...cluster, averagePrice: avgPrice }
          markerContent = createClusterMarkerContent(tempCluster, style, transactionFilter)
        }

        // 가격 정보가 없어서 빈 마커 콘텐츠가 반환된 경우 스킵
        if (!markerContent || markerContent.trim() === '') {
          if (index < 5) console.log('[useMap] Empty marker content for cluster:', index)
          return
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
              onPropertySelect(property)
              kakaoMap.setCenter(position)
            } else {
              // Zoom in to cluster
              kakaoMap.setCenter(position)
              kakaoMap.setLevel(Math.max(1, currentZoom - 2))
            }
          })
        }

      } catch (error) {
        console.error('Error creating marker:', error)
      }
    })

    console.log('[useMap] Markers created:', newMarkers.length)
    markersRef.current = newMarkers
  }, [clusters, currentZoom, onPropertySelect, transactionFilter])

  // Update markers when map or clusters change
  useEffect(() => {
    if (map && clusters.length >= 0) {
      setupPropertyMarkers(map)
    }
  }, [map, clusters, setupPropertyMarkers])

  return {
    map,
    currentZoom,
    loading,
    clusters
  }
}
