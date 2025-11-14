// Clustering utilities for real estate properties
export interface Property {
  id: string
  name: string
  type: "office" | "residential" // 이게 무슨 타입이지 ?
  property_type?: string  // 부동산 유형 (아파트, 오피스텔, 동 평균, 구 평균 등)
  district: string
  dong: string
  price: {
    sale: { min: number; max: number; minFormatted: string; maxFormatted: string }
    jeonse: { min: number; max: number; minFormatted: string; maxFormatted: string }
    monthly: { min: number; max: number; minFormatted: string; maxFormatted: string }
  }
  area: { min: number; max: number; summary: string }
  details: {
    households: number
    buildings: number
    completionDate: string
    summary: string
  }
  transactions: { sale: number; jeonse: number; monthly: number; total: number }
  coordinates: { lat: number; lng: number }
}

export interface ClusterPoint {
  lat: number
  lng: number
  properties: Property[]
  id: string
}

export interface Cluster {
  center: { lat: number; lng: number }
  properties: Property[]
  bounds: {
    north: number
    south: number
    east: number
    west: number
  }
  size: "small" | "medium" | "large" | "xlarge"
  count: number
  averagePrice?: number
  // 거래 유형별 평균 가격
  averagePricesByTransaction?: {
    매매?: number  // 억원 단위
    전세?: number  // 억원 단위
    월세?: number  // 만원 단위
  }
  // 부동산 유형별 평균 가격
  averagePricesByPropertyType?: {
    [propertyType: string]: {
      매매?: number  // 억원 단위
      전세?: number  // 억원 단위
      월세?: number  // 만원 단위
    }
  }
  dongName?: string
  complexName?: string
  districtName?: string
  clusterLevel?: string
}

// Helper function to format monthly rent price
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

// Calculate distance between two points using Haversine formula
export function calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371 // Earth's radius in kilometers
  const dLat = (lat2 - lat1) * (Math.PI / 180)
  const dLng = (lng2 - lng1) * (Math.PI / 180)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.sin(dLng / 2) * Math.sin(dLng / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

// Generate random coordinates within district bounds for demo purposes
export function generatePropertyCoordinates(district: string, count: number): ClusterPoint[] {
  const districtBounds: Record<string, { lat: [number, number]; lng: [number, number] }> = {
    강남구: { lat: [37.495, 37.52], lng: [126.99, 127.065] },
    서초구: { lat: [37.48, 37.505], lng: [126.96, 127.05] },
    송파구: { lat: [37.495, 37.52], lng: [127.06, 127.13] },
  }

  const bounds = districtBounds[district]
  if (!bounds) return []

  const points: ClusterPoint[] = []
  for (let i = 0; i < count; i++) {
    const lat = bounds.lat[0] + Math.random() * (bounds.lat[1] - bounds.lat[0])
    const lng = bounds.lng[0] + Math.random() * (bounds.lng[1] - bounds.lng[0])

    points.push({
      lat,
      lng,
      properties: [],
      id: `${district}-${i}`,
    })
  }

  return points
}

// 클라이언트 사이드 클러스터링 (지도 렌더링용)
export function clusterProperties(properties: any[], zoomLevel: number, transactionFilter?: string): Cluster[] {
  if (!properties || properties.length === 0) {
    return [];
  }

  // API에서 이미 집계된 데이터(dong/gu)가 온 경우, 그대로 표시
  // type === "dong" 또는 "gu"인 데이터는 API에서 이미 집계된 것
  const hasAggregatedData = properties.some(p => p.type === "dong" || p.type === "gu");

  if (hasAggregatedData) {
    // 집계된 데이터를 Cluster 형식으로 변환하여 그대로 반환
    return properties
      .filter(p => p.type === "dong" || p.type === "gu")
      .map(property => {
        const avgPrice = getPropertyPrice(property, transactionFilter);

        return {
          center: {
            lat: property.latitude,
            lng: property.longitude
          },
          properties: [property],
          bounds: {
            north: property.latitude,
            south: property.latitude,
            east: property.longitude,
            west: property.longitude
          },
          size: "medium" as const,
          count: property.count || 1,
          averagePrice: avgPrice,
          districtName: property.gu,
          dongName: property.dong,
          clusterLevel: property.type === "gu" ? "district" : "dong",
          averagePricesByTransaction: calculateAveragePricesByTransaction([property])
        }
      });
  }

  // 개별 매물 데이터만 클러스터링 적용
  // Zoom level에 따른 클러스터링 파라미터 결정
  // Kakao Map: level이 작을수록 확대된 상태 (1=최대확대, 14=최대축소)
  // 줌 레벨 4 이하: 개별 마커만 표시
  // 줌 레벨 5-6: 동별 클러스터링
  // 줌 레벨 7-8: 구별 클러스터링 (API에서 제공)
  // 줌 레벨 9+: 개별 마커 (축소 상태이지만 API가 처리 안함)
  const getClusteringParams = (zoom: number) => {
    if (zoom < 5) return { minClusterSize: 1, clusterBy: "individual" }; // 개별 표시 (레벨 4까지)
    if (zoom < 7) return { minClusterSize: 1, clusterBy: "dong" };       // 동별 클러스터링 (레벨 5-6)
    return { minClusterSize: 1, clusterBy: "individual" };                // 개별 표시 (레벨 7 이상은 API에서 처리)
  }

  const params = getClusteringParams(zoomLevel)
  const { minClusterSize, clusterBy } = params

  // Individual markers (no clustering)
  if (clusterBy === "individual") {
    return properties.map(property => ({
      center: {
        lat: property.위도 || property.latitude,
        lng: property.경도 || property.longitude
      },
      properties: [property],
      bounds: {
        north: property.위도 || property.latitude,
        south: property.위도 || property.latitude,
        east: property.경도 || property.longitude,
        west: property.경도 || property.longitude
      },
      size: "small" as const,
      count: 1,
      averagePrice: getPropertyPrice(property, transactionFilter),
      clusterLevel: "individual"
    }))
  }

  // Group properties by cluster key
  const groups: { [key: string]: any[] } = {}

  properties.forEach(property => {
    let key = ""
    if (clusterBy === "district") {
      key = property.구 || property.district || ""
    } else if (clusterBy === "dong") {
      // '구' 정보가 없어도 '동' 이름만으로 클러스터링이 가능하도록 수정
      // 송파구 데이터에서 '구' 정보가 누락되어 하나의 클러스터로 합쳐지는 문제 해결
      const gu = property.구 || property.district || "";
      const dong = property.동 || property.dong || "";
      key = gu ? `${gu}_${dong}` : dong;
    }

    if (key) {
      if (!groups[key]) groups[key] = []
      groups[key].push(property)
    }
  })

  // Create clusters from groups
  const clusters: Cluster[] = []

  Object.entries(groups).forEach(([, groupProps]) => {
    if (groupProps.length < minClusterSize) {
      // Add as individual markers
      groupProps.forEach(prop => {
        const lat = prop.위도 || prop.latitude
        const lng = prop.경도 || prop.longitude
        if (lat && lng) {
          clusters.push({
            center: { lat, lng },
            properties: [prop],
            bounds: { north: lat, south: lat, east: lng, west: lng },
            size: "small" as const,
            count: 1,
            averagePrice: getPropertyPrice(prop, transactionFilter),
            clusterLevel: "individual"
          })
        }
      })
      return
    }

    // Calculate cluster center and bounds
    const validProps = groupProps.filter(p => (p.위도 || p.latitude) && (p.경도 || p.longitude))
    if (validProps.length === 0) return

    const lats = validProps.map(p => p.위도 || p.latitude)
    const lngs = validProps.map(p => p.경도 || p.longitude)

    const centerLat = lats.reduce((sum, lat) => sum + lat, 0) / lats.length
    const centerLng = lngs.reduce((sum, lng) => sum + lng, 0) / lngs.length

    // Calculate average prices by transaction type
    let avgPrice: number | undefined;

    if (clusterBy === 'district') {
      // '구' 클러스터링 시, '동'별 평균 가격을 먼저 구한 후, 그 평균들의 평균을 계산
      const dongGroups: { [dongName: string]: any[] } = {};
      validProps.forEach(p => {
        const dongKey = p.동 || p.dong || 'unknown';
        if (!dongGroups[dongKey]) {
          dongGroups[dongKey] = [];
        }
        dongGroups[dongKey].push(p);
      });

      const dongAveragePrices: number[] = [];
      Object.values(dongGroups).forEach(dongProps => {
        const dongPrices = dongProps.map(p => getPropertyPrice(p, transactionFilter)).filter((p): p is number => p !== undefined && p > 0);
        if (dongPrices.length > 0) {
          const dongAvg = dongPrices.reduce((sum, p) => sum + p, 0) / dongPrices.length;
          dongAveragePrices.push(dongAvg);
        }
      });

      avgPrice = dongAveragePrices.length > 0 ? dongAveragePrices.reduce((sum, p) => sum + p, 0) / dongAveragePrices.length : undefined;
    } else {
      const prices = validProps.map(p => getPropertyPrice(p, transactionFilter)).filter((p): p is number => p !== undefined && p > 0)
      avgPrice = prices.length > 0 ? prices.reduce((sum, p) => sum + p, 0) / prices.length : undefined
    }

    // Calculate size
    let size: "small" | "medium" | "large" | "xlarge" = "small"
    if (validProps.length >= 200) size = "xlarge"
    else if (validProps.length >= 100) size = "large"
    else if (validProps.length >= 50) size = "medium"

    // Extract names based on cluster level (only district and dong)
    let districtName: string | undefined = undefined
    let dongName: string | undefined = undefined

    if (clusterBy === "district") {
      districtName = validProps[0].구 || validProps[0].district || "지역"
    } else if (clusterBy === "dong") {
      districtName = validProps[0].구 || validProps[0].district
      dongName = validProps[0].동 || validProps[0].dong || "동"
    }

    clusters.push({
      center: { lat: centerLat, lng: centerLng },
      properties: validProps,
      bounds: {
        north: Math.max(...lats),
        south: Math.min(...lats),
        east: Math.max(...lngs),
        west: Math.min(...lngs)
      },
      size,
      count: validProps.length,
      averagePrice: avgPrice,
      districtName,
      dongName,
      clusterLevel: clusterBy,
      averagePricesByTransaction: calculateAveragePricesByTransaction(validProps)
    })
  })

  return clusters
}

// Helper function to get property price based on transaction filter
function getPropertyPrice(property: any, transactionFilter?: string): number | undefined {
  // Check if this is aggregate data (dong/gu 최저가)
  const isAggregateData = property.property_type === "동 최저가" || property.property_type === "구 최저가"

  if (isAggregateData) {
    // Handle aggregate data with *_eok fields (already in string format like "5.2억")
    if (transactionFilter === "매매") {
      const priceStr = property.sale_max_price_eok
      if (priceStr && priceStr !== '') {
        // Parse "5.2억" -> 5.2 (억원 단위)
        const numStr = priceStr.replace('억', '').trim()
        return parseFloat(numStr)
      }
    } else if (transactionFilter === "전세") {
      const priceStr = property.jeonse_max_price_eok
      if (priceStr && priceStr !== '') {
        const numStr = priceStr.replace('억', '').trim()
        return parseFloat(numStr)
      }
    } else if (transactionFilter === "월세") {
      const priceStr = property.rent_max_price_eok
      if (priceStr && priceStr !== '') {
        const numStr = priceStr.replace('억', '').trim()
        const eokValue = parseFloat(numStr)
        // 억원 단위를 만원 단위로 변환 (월세는 만원 단위로 처리)
        return eokValue * 10000
      }
    }

    // Default priority for aggregate data: sale > jeonse > rent
    const saleEok = property.sale_max_price_eok
    if (saleEok && saleEok !== '') {
      const numStr = saleEok.replace('억', '').trim()
      return parseFloat(numStr)
    }
    const jeonseEok = property.jeonse_max_price_eok
    if (jeonseEok && jeonseEok !== '') {
      const numStr = jeonseEok.replace('억', '').trim()
      return parseFloat(numStr)
    }
    const rentEok = property.rent_max_price_eok
    if (rentEok && rentEok !== '') {
      const numStr = rentEok.replace('억', '').trim()
      const eokValue = parseFloat(numStr)
      // 억원 단위를 만원 단위로 변환
      return eokValue * 10000
    }
    return undefined
  }

  // Handle individual property data with raw price fields
  if (transactionFilter === "매매") {
    const price = property.매매_최고가 || property.매매_최저가
    return price ? parseFloat(price) / 10000 : undefined // Convert 만원 to 억원
  } else if (transactionFilter === "전세") {
    const price = property.전세_최고가 || property.전세_최저가
    return price ? parseFloat(price) / 10000 : undefined
  } else if (transactionFilter === "월세") {
    const price = property.월세_최고가 || property.월세_최저가
    return price ? parseFloat(price) : undefined // Keep in 만원
  }

  // Default: prioritize sale > jeonse > monthly
  const salePrice = property.매매_최고가
  if (salePrice && parseFloat(salePrice) > 0) {
    return parseFloat(salePrice) / 10000
  }
  const jeonsePrice = property.전세_최고가
  if (jeonsePrice && parseFloat(jeonsePrice) > 0) {
    return parseFloat(jeonsePrice) / 10000
  }
  const monthlyPrice = property.월세_최고가
  if (monthlyPrice && parseFloat(monthlyPrice) > 0) {
    return parseFloat(monthlyPrice)
  }
  return undefined
}

// Calculate average prices by transaction type
function calculateAveragePricesByTransaction(properties: any[]): {
  매매?: number
  전세?: number
  월세?: number
} {
  const result: any = {}

  // Check if properties are aggregate data
  const isAggregateData = properties.length > 0 &&
    (properties[0].property_type === "동 최저가" || properties[0].property_type === "구 최저가")

  if (isAggregateData) {
    // For aggregate data, use *_eok fields
    const salePrices = properties
      .map(p => {
        const priceStr = p.sale_max_price_eok
        if (priceStr && priceStr !== '') {
          const numStr = priceStr.replace('억', '').trim()
          return parseFloat(numStr)
        }
        return 0
      })
      .filter(p => p > 0)
    if (salePrices.length > 0) {
      result.매매 = salePrices.reduce((sum, p) => sum + p, 0) / salePrices.length
    }

    const jeonsePrices = properties
      .map(p => {
        const priceStr = p.jeonse_max_price_eok
        if (priceStr && priceStr !== '') {
          const numStr = priceStr.replace('억', '').trim()
          return parseFloat(numStr)
        }
        return 0
      })
      .filter(p => p > 0)
    if (jeonsePrices.length > 0) {
      result.전세 = jeonsePrices.reduce((sum, p) => sum + p, 0) / jeonsePrices.length
    }

    const monthlyPrices = properties
      .map(p => {
        const priceStr = p.rent_max_price_eok
        if (priceStr && priceStr !== '') {
          const numStr = priceStr.replace('억', '').trim()
          const eokValue = parseFloat(numStr)
          // 억원 단위를 만원 단위로 변환 (1억 = 10,000만원)
          return eokValue * 10000
        }
        return 0
      })
      .filter(p => p > 0)
    if (monthlyPrices.length > 0) {
      result.월세 = monthlyPrices.reduce((sum, p) => sum + p, 0) / monthlyPrices.length
    }
  } else {
    // For individual property data, use raw price fields
    // 매매
    const salePrices = properties
      .map(p => {
        const price = p.매매_최고가 || p.매매_최저가
        return price ? parseFloat(price) / 10000 : 0
      })
      .filter(p => p > 0)
    if (salePrices.length > 0) {
      result.매매 = salePrices.reduce((sum, p) => sum + p, 0) / salePrices.length
    }

    // 전세
    const jeonsePrices = properties
      .map(p => {
        const price = p.전세_최고가 || p.전세_최저가
        return price ? parseFloat(price) / 10000 : 0
      })
      .filter(p => p > 0)
    if (jeonsePrices.length > 0) {
      result.전세 = jeonsePrices.reduce((sum, p) => sum + p, 0) / jeonsePrices.length
    }

    // 월세
    const monthlyPrices = properties
      .map(p => {
        const price = p.월세_최고가 || p.월세_최저가
        return price ? parseFloat(price) : 0
      })
      .filter(p => p > 0)
    if (monthlyPrices.length > 0) {
      result.월세 = monthlyPrices.reduce((sum, p) => sum + p, 0) / monthlyPrices.length
    }
  }

  return result
}

// Hogangnono-style cluster marker styling with price indicators
export function getClusterStyle(count: number, zoomLevel: number = 7, averagePrice?: number) {
  const isHighZoom = zoomLevel > 14;
  const isDetailedView = zoomLevel > 16;
  
  // Price-based color coding (similar to hogangnono)
  const getPriceColor = (price?: number) => {
    if (!price) return "#6b7280"; // Gray for no price data
    if (price >= 50) return "#dc2626"; // Red for expensive (50억+)
    if (price >= 30) return "#f59e0b"; // Orange for high (30-50억)
    if (price >= 15) return "#10b981"; // Green for medium (15-30억)
    return "#3b82f6"; // Blue for affordable (<15억)
  };
  
  // Single property styling - hogangnono uses simple dots
  if (count === 1) {
    return {
      backgroundColor: getPriceColor(averagePrice),
      color: "#ffffff",
      size: isHighZoom ? "large" : "small" as const,
      icon: "●",
      showDetails: isDetailedView,
      borderColor: "rgba(255,255,255,0.8)",
      opacity: 1,
      fontSize: isHighZoom ? "16px" : "12px"
    }
  } 
  
  // Small clusters (2-9 properties) - use average price for color
  if (count < 10) {
    const bgColor = getPriceColor(averagePrice);
    return {
      backgroundColor: bgColor,
      borderColor: bgColor,
      color: "#ffffff",
      size: "medium" as const,
      icon: count.toString(),
      showDetails: false,
      opacity: 0.9,
      fontSize: "14px"
    }
  } 
  
  // Medium clusters (10-49 properties)
  if (count < 50) {
    const bgColor = getPriceColor(averagePrice);
    return {
      backgroundColor: bgColor,
      borderColor: bgColor,
      color: "#ffffff", 
      size: "large" as const,
      icon: count.toString(),
      showDetails: false,
      opacity: 0.9,
      fontSize: "16px"
    }
  }
  
  // Large clusters (50+ properties)
  const bgColor = getPriceColor(averagePrice);
  return {
    backgroundColor: bgColor,
    borderColor: bgColor,
    color: "#ffffff",
    size: "xlarge" as const,
    icon: count.toString(),
    showDetails: false,
    opacity: 0.9,
    fontSize: "18px"
  }
}

// Enhanced office property marker style
export function getOfficeMarkerStyle(count: number, zoomLevel: number = 7) {
  const isHighZoom = zoomLevel <= 4;
  const isDetailedView = zoomLevel <= 3;

  return {
    backgroundColor: "#f59e0b", // Orange for offices
    color: "#ffffff",
    size: isHighZoom ? "large" : "medium" as const,
    icon: isHighZoom ? "O" : "●",
    showDetails: isDetailedView,
    borderColor: "rgba(255,255,255,0.3)",
    opacity: 0.9
  }
}

// Enhanced detailed property marker with Leaflet-inspired popup design
export function createDetailedMarkerContent(property: any, transactionFilter: string = "전체"): string {
  // Handle both new Property interface and legacy property format
  const name = property.name || property.단지명 || 'Unknown Property';
  const district = property.district || property.구 || '';
  const dong = property.dong || property.동 || '';
  const isOffice = property.type === 'office' || name.includes('오피스');
  
  // Price handling for both formats
  let primaryPrice = 'N/A';
  let priceType = '';
  
  if (property.price) {
    // New format
    if (property.price.sale.minFormatted) {
      primaryPrice = property.price.sale.minFormatted;
      priceType = '매매';
    } else if (property.price.jeonse.minFormatted) {
      primaryPrice = property.price.jeonse.minFormatted;
      priceType = '전세';
    } else if (property.price.monthly.minFormatted) {
      primaryPrice = property.price.monthly.minFormatted;
      priceType = '월세';
    }
  } else {
    // Legacy format - use actual CSV data fields
    const saleHighEok = property.sale_max_price_eok;
    const saleLowEok = property.sale_min_price_eok;
    const jeonseHighEok = property.jeonse_max_price_eok;
    const jeonseLowEok = property.jeonse_min_price_eok;
    // Use raw 월세 values in 만원 units, not the formatted _억원 strings
    const monthlyHigh = property.rent_max_price;
    const monthlyLow = property.rent_min_price;

    const isValidEok = (price: any) => price && price !== '' && price !== '0';
    const isValidManwon = (price: any) => price && price !== '' && price !== '0' && parseFloat(price) > 0;

    // Show price based on transactionFilter
    if (transactionFilter === "매매" && isValidEok(saleHighEok)) {
      primaryPrice = saleLowEok !== saleHighEok ? `${saleLowEok}~${saleHighEok}` : `${saleHighEok}`;
      priceType = '매매';
    } else if (transactionFilter === "전세" && isValidEok(jeonseHighEok)) {
      primaryPrice = jeonseLowEok !== jeonseHighEok ? `${jeonseLowEok}~${jeonseHighEok}` : `${jeonseHighEok}`;
      priceType = '전세';
    } else if (transactionFilter === "월세" && isValidManwon(monthlyHigh)) {
      // Format monthly rent properly from raw 만원 values
      const highPrice = parseFloat(monthlyHigh);
      const lowPrice = parseFloat(monthlyLow || monthlyHigh); // fallback to high if low is missing
      primaryPrice = lowPrice !== highPrice ? `${formatMonthlyPrice(lowPrice)}~${formatMonthlyPrice(highPrice)}` : formatMonthlyPrice(highPrice);
      priceType = '월세';
    } else if (isValidEok(saleHighEok)) { // Default priority when filter is "전체"
      primaryPrice = saleLowEok !== saleHighEok ? `${saleLowEok}~${saleHighEok}` : `${saleHighEok}`;
      priceType = '매매';
    } else if (isValidEok(jeonseHighEok)) {
      primaryPrice = jeonseLowEok !== jeonseHighEok ? `${jeonseLowEok}~${jeonseHighEok}` : `${jeonseHighEok}`;
      priceType = '전세';
    } else if (isValidManwon(monthlyHigh)) {
      const highPrice = parseFloat(monthlyHigh);
      const lowPrice = parseFloat(monthlyLow || monthlyHigh);
      primaryPrice = lowPrice !== highPrice ? `${formatMonthlyPrice(lowPrice)}~${formatMonthlyPrice(highPrice)}` : formatMonthlyPrice(highPrice);
      priceType = '월세';
    } else {
      primaryPrice = '정보없음';
      priceType = '';
    }
  }


  // Area information
  const areaInfo = property.area?.summary || property.면적요약 || '';
  const transactions = property.transactions?.total || property.총_거래건수 || 0;
  
  // Simple, clean individual property marker for high zoom
  return `
    <div style="
      background: ${isOffice ? '#f59e0b' : '#10b981'};
      color: white;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 10px;
      font-weight: 600;
      box-shadow: 0 3px 12px rgba(0,0,0,0.3);
      cursor: pointer;
      max-width: 160px;
      text-align: center;
      border: 2px solid rgba(255,255,255,0.8);
      position: relative;
      transform: translateY(-4px);
    ">
      <div style="font-size: 11px; font-weight: 700; margin-bottom: 3px;">
        ${name.length > 15 ? name.substring(0, 15) + '...' : name}
      </div>
      
      <div style="font-size: 12px; font-weight: bold; margin-bottom: 2px;">
        ${primaryPrice}
      </div>
      
      ${priceType ? `<div style="font-size: 9px; opacity: 0.9; background: rgba(255,255,255,0.2); padding: 1px 4px; border-radius: 4px; display: inline-block;">${priceType}</div>` : ''}
    </div>
  `;
}

// Create Naver-style cluster marker content
export function createClusterMarkerContent(cluster: Cluster, style: any, transactionFilter?: string): string {
  const sizeMap: Record<string, { width: number; height: number; padding: string }> = {
    small: { width: 60, height: 45, padding: '8px 10px' },
    medium: { width: 80, height: 55, padding: '10px 14px' },
    large: { width: 100, height: 65, padding: '12px 16px' },
    xlarge: { width: 120, height: 75, padding: '14px 18px' }
  };

  const size = sizeMap[style.size as keyof typeof sizeMap] || sizeMap.medium;

  // Naver-style dong cluster display with blue/green/orange colors
  if (cluster.count > 1) {
    // Build detailed price text based on transaction filter
    const priceDetails: string[] = [];

    // 필터에 따라 선택된 거래 유형의 가격만 표시
    if (transactionFilter === "매매" && cluster.averagePricesByTransaction?.매매) {
      const price = cluster.averagePricesByTransaction.매매;
      const text = price % 1 === 0 ? `매매 ${Math.round(price)}억` : `매매 ${price.toFixed(1)}억`;
      priceDetails.push(text);
    } else if (transactionFilter === "전세" && cluster.averagePricesByTransaction?.전세) {
      const price = cluster.averagePricesByTransaction.전세;
      const text = price % 1 === 0 ? `전세 ${Math.round(price)}억` : `전세 ${price.toFixed(1)}억`;
      priceDetails.push(text);
    } else if (transactionFilter === "월세" && cluster.averagePricesByTransaction?.월세) {
      const price = cluster.averagePricesByTransaction.월세;
      priceDetails.push(`월세 ${formatMonthlyPrice(price)}`);
    } else if (transactionFilter === "전체") {
      // "전체" 필터일 때만 모든 가격 표시
      if (cluster.averagePricesByTransaction?.매매) {
        const price = cluster.averagePricesByTransaction.매매;
        const text = price % 1 === 0 ? `매매 ${Math.round(price)}억` : `매매 ${price.toFixed(1)}억`;
        priceDetails.push(text);
      }

      if (cluster.averagePricesByTransaction?.전세) {
        const price = cluster.averagePricesByTransaction.전세;
        const text = price % 1 === 0 ? `전세 ${Math.round(price)}억` : `전세 ${price.toFixed(1)}억`;
        priceDetails.push(text);
      }

      if (cluster.averagePricesByTransaction?.월세) {
        const price = cluster.averagePricesByTransaction.월세;
        priceDetails.push(`월세 ${formatMonthlyPrice(price)}`);
      }
    }

    // Build property type breakdown
    const propertyTypeDetails: string[] = [];
    if (cluster.averagePricesByPropertyType) {
      Object.entries(cluster.averagePricesByPropertyType).forEach(([propType, prices]) => {
        const priceStr: string[] = [];
        if (prices.매매) {
          const p = prices.매매;
          priceStr.push(p % 1 === 0 ? `${Math.round(p)}억` : `${p.toFixed(1)}억`);
        }
        if (prices.전세 && !prices.매매) {
          const p = prices.전세;
          priceStr.push(p % 1 === 0 ? `${Math.round(p)}억` : `${p.toFixed(1)}억`);
        }
        if (prices.월세 && !prices.매매 && !prices.전세) {
          priceStr.push(formatMonthlyPrice(prices.월세));
        }

        if (priceStr.length > 0) {
          propertyTypeDetails.push(`${propType}: ${priceStr[0]}`);
        }
      });
    }

    // Main display price (based on active filter with fallback to sale price)
    let avgPriceText = '';

    // 필터에 따라 해당하는 가격 표시, 없으면 매매가로 폴백
    if (transactionFilter === "매매") {
      if (cluster.averagePricesByTransaction?.매매) {
        const price = cluster.averagePricesByTransaction.매매;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      }
    } else if (transactionFilter === "전세") {
      if (cluster.averagePricesByTransaction?.전세) {
        const price = cluster.averagePricesByTransaction.전세;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      } else if (cluster.averagePricesByTransaction?.매매) {
        // 전세가 없으면 매매가로 폴백
        const price = cluster.averagePricesByTransaction.매매;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      }
    } else if (transactionFilter === "월세") {
      if (cluster.averagePricesByTransaction?.월세) {
        const price = cluster.averagePricesByTransaction.월세;
        avgPriceText = formatMonthlyPrice(price);
      } else if (cluster.averagePricesByTransaction?.매매) {
        // 월세가 없으면 매매가로 폴백
        const price = cluster.averagePricesByTransaction.매매;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      }
    } else if (transactionFilter === "전체") {
      // "전체" 필터일 때는 우선순위: 매매 > 전세 > 월세
      if (cluster.averagePricesByTransaction?.매매) {
        const price = cluster.averagePricesByTransaction.매매;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      } else if (cluster.averagePricesByTransaction?.전세) {
        const price = cluster.averagePricesByTransaction.전세;
        avgPriceText = price % 1 === 0 ? `${Math.round(price)}억` : `${price.toFixed(1)}억`;
      } else if (cluster.averagePricesByTransaction?.월세) {
        const price = cluster.averagePricesByTransaction.월세;
        avgPriceText = formatMonthlyPrice(price);
      }
    }

    // 가격 정보가 없으면 마커를 표시하지 않음
    if (!avgPriceText) {
      return '';
    }

    // Display name based on cluster level (only district and dong)
    let displayName = '지역';
    if (cluster.clusterLevel === "district" && cluster.districtName) {
      displayName = cluster.districtName;
    } else if (cluster.clusterLevel === "dong") {
      if (cluster.dongName && cluster.districtName) {
        displayName = `${cluster.districtName} ${cluster.dongName}`;
      } else if (cluster.dongName) {
        displayName = cluster.dongName;
      } else if (cluster.districtName) {
        displayName = cluster.districtName;
      }
    } else if (cluster.districtName) {
      displayName = cluster.districtName;
    } else if (cluster.dongName) {
      displayName = cluster.dongName;
    }

    // Naver-style color selection based on average price
    let bgColor = '#3182f6'; // Default blue
    if (cluster.averagePrice) {
      if (cluster.averagePrice >= 30) bgColor = '#ff9500'; // Orange for expensive
      else if (cluster.averagePrice >= 15) bgColor = '#34c759'; // Green for medium
    }

    // Build tooltip content only with available price info
    const tooltipContent = priceDetails.length > 0
      ? `가격 정보:\n${priceDetails.join('\n')}`
      : '가격 정보 없음';

    return `
      <div style="
        background: ${bgColor};
        color: white;
        padding: ${size.padding};
        border-radius: 4px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        cursor: pointer;
        font-weight: 700;
        text-align: center;
        min-width: ${size.width}px;
        transition: all 0.2s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        position: relative;
      "
      onmouseover="this.style.transform='scale(1.05)'; this.style.zIndex='10000';"
      onmouseout="this.style.transform='scale(1)'; this.style.zIndex='1';"
      title="${tooltipContent.replace(/\n/g, '&#10;')}">
        <div style="font-size: 13px; font-weight: 700; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          ${displayName}
        </div>
        <div style="font-size: 16px; font-weight: 700; letter-spacing: -0.5px;">
          ${avgPriceText}
        </div>
        <div style="
          position: absolute;
          bottom: -4px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 4px solid transparent;
          border-right: 4px solid transparent;
          border-top: 4px solid ${bgColor};
        "></div>
      </div>
    `;
  }

  // Small circle for individual clusters in medium zoom
  return `
    <div style="
      background: #3182f6;
      width: ${size.width}px;
      height: ${size.height}px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 6px rgba(0,0,0,0.25);
      color: white;
      font-weight: 700;
      font-size: ${style.fontSize || '14px'};
      cursor: pointer;
      transition: all 0.2s ease;
    " onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
      ${style.icon}
    </div>
  `;
}

// Filter properties based on criteria
export function filterProperties(
  properties: any[],
  filters: {
    priceRange?: [number, number]
    propertyType?: string
    district?: string
    transactionType?: "sale" | "rent" | "monthly"
  },
) {
  return properties.filter((property) => {
    // District filter
    if (filters.district && property.구 !== filters.district) {
      return false
    }

    // Price range filter (simplified - would need proper parsing in real app)
    if (filters.priceRange && filters.transactionType) {
      const priceField =
        filters.transactionType === "sale"
          ? "매매_최저가"
          : filters.transactionType === "rent"
            ? "전세_최저가"
            : "월세_최저가"

      const price = Number.parseInt(property[priceField] || "0")
      if (price < filters.priceRange[0] || price > filters.priceRange[1]) {
        return false
      }
    }

    return true
  })
}
