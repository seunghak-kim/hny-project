// Clustering utilities for real estate properties
export interface Property {
  id: string
  name: string
  type: "office" | "residential"
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
  dongName?: string
  complexName?: string
  districtName?: string
  clusterLevel?: string
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

// Enhanced clustering algorithm with better performance and accuracy
export function clusterProperties(properties: any[], zoomLevel: number): Cluster[] {
  if (properties.length === 0) return []

  // Hogangnono-style progressive clustering (Kakao Map: lower zoom = more zoomed in)
  const getClusteringParams = (zoom: number) => {
    if (zoom >= 5) return { distance: 0.02, minClusterSize: 1, clusterByDong: true, clusterLevel: 'dong' }      // Far - dong level clusters with avg price
    return { distance: 0, minClusterSize: 1, clusterByDong: false, clusterLevel: 'individual' }                  // Close - individual properties with details
  }

  const { distance: maxDistance, minClusterSize, clusterByDong, clusterLevel } = getClusteringParams(zoomLevel)
  
  const clusters: Cluster[] = []
  const processed = new Set<number>()

  // Use actual coordinates from CSV data or fallback to district-based generation
  const getPropertyCoordinates = (property: any) => {
    // First check for actual coordinates from CSV (위도, 경도)
    if (property.위도 && property.경도 && !isNaN(property.위도) && !isNaN(property.경도)) {
      return { lat: property.위도, lng: property.경도 }
    }
    
    // Legacy coordinate format
    if (property.coordinates?.lat && property.coordinates?.lng) {
      return { lat: property.coordinates.lat, lng: property.coordinates.lng }
    }
    
    // Fallback: Generate coordinates based on district with some randomization
    const districtBase = {
      '강남구': { lat: 37.5172, lng: 127.0473 },
      '서초구': { lat: 37.4837, lng: 127.0324 },
      '송파구': { lat: 37.5145, lng: 127.1059 }
    }
    
    const district = property.district || property.구 || '강남구'
    const base = districtBase[district as keyof typeof districtBase] || districtBase['강남구']
    
    // Add randomization based on property name hash for consistency
    const hash = property.단지명 ? property.단지명.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0) : 0
    const latOffset = (hash % 100) / 10000 - 0.005  // ±0.005 degrees
    const lngOffset = ((hash * 7) % 100) / 10000 - 0.005  // ±0.005 degrees
    
    return {
      lat: base.lat + latOffset,
      lng: base.lng + lngOffset
    }
  }

  // If zoom is high enough, return individual properties without clustering
  if (maxDistance === 0) {
    return properties.map(property => {
      const coords = getPropertyCoordinates(property)
      return {
        center: coords,
        properties: [property],
        bounds: {
          north: coords.lat,
          south: coords.lat,
          east: coords.lng,
          west: coords.lng,
        },
        size: "small" as const,
        count: 1
      }
    })
  }

  // Pre-calculate coordinates and sort by district for efficient clustering
  const propertiesWithCoords = properties.map((property, index) => ({
    property,
    coords: getPropertyCoordinates(property),
    originalIndex: index,
    district: property.구 || '기타'
  }))

  // Progressive clustering based on zoom level
  if (clusterByDong) {
    const levelGroups = new Map<string, typeof propertiesWithCoords>()
    
    // Only dong-level clustering for far zoom
    propertiesWithCoords.forEach(item => {
      const dongKey = `${item.district}_${item.property.동 || '기타'}`;
      if (!levelGroups.has(dongKey)) {
        levelGroups.set(dongKey, []);
      }
      levelGroups.get(dongKey)!.push(item);
    });

    // Create clusters based on grouping level
    levelGroups.forEach((groupProperties, groupKey) => {
      if (groupProperties.length >= minClusterSize) {
        const allLats = groupProperties.map(item => item.coords.lat)
        const allLngs = groupProperties.map(item => item.coords.lng)
        
        const cluster: Cluster = {
          center: {
            lat: allLats.reduce((sum, lat) => sum + lat, 0) / allLats.length,
            lng: allLngs.reduce((sum, lng) => sum + lng, 0) / allLngs.length
          },
          properties: groupProperties.map(item => item.property),
          bounds: {
            north: Math.max(...allLats),
            south: Math.min(...allLats),
            east: Math.max(...allLngs),
            west: Math.min(...allLngs),
          },
          size: "medium",
          count: groupProperties.length,
          dongName: groupProperties[0].property.동 || '기타',
          clusterLevel: 'dong'
        }

        // Determine cluster size
        if (cluster.count >= 100) cluster.size = "xlarge"
        else if (cluster.count >= 50) cluster.size = "large"
        else if (cluster.count >= 10) cluster.size = "medium"
        else cluster.size = "small"

        clusters.push(cluster)
        groupProperties.forEach(item => processed.add(item.originalIndex))
      }
    })
  }

  // Group by district for distance-based clustering
  const districtGroups = new Map<string, typeof propertiesWithCoords>()
  propertiesWithCoords.forEach(item => {
    if (!processed.has(item.originalIndex)) {
      if (!districtGroups.has(item.district)) {
        districtGroups.set(item.district, [])
      }
      districtGroups.get(item.district)!.push(item)
    }
  })

  // Process remaining properties with distance-based clustering
  districtGroups.forEach(districtProperties => {
    districtProperties.forEach((item, index) => {
      if (processed.has(item.originalIndex)) return

      const coords = item.coords
      const cluster: Cluster = {
        center: { ...coords },
        properties: [item.property],
        bounds: {
          north: coords.lat,
          south: coords.lat,
          east: coords.lng,
          west: coords.lng,
        },
        size: "small",
        count: 1
      }

      processed.add(item.originalIndex)

      // Find nearby properties in the same district
      for (let i = index + 1; i < districtProperties.length; i++) {
        const otherItem = districtProperties[i]
        if (processed.has(otherItem.originalIndex)) continue

        const distance = calculateDistance(coords.lat, coords.lng, otherItem.coords.lat, otherItem.coords.lng)

        if (distance <= maxDistance) {
          cluster.properties.push(otherItem.property)
          processed.add(otherItem.originalIndex)

          // Update bounds
          cluster.bounds.north = Math.max(cluster.bounds.north, otherItem.coords.lat)
          cluster.bounds.south = Math.min(cluster.bounds.south, otherItem.coords.lat)
          cluster.bounds.east = Math.max(cluster.bounds.east, otherItem.coords.lng)
          cluster.bounds.west = Math.min(cluster.bounds.west, otherItem.coords.lng)

          cluster.count = cluster.properties.length
        }
      }

      // Only create cluster if it meets minimum size requirement
      if (cluster.count >= minClusterSize || zoomLevel > 14) {
        // Recalculate center as centroid
        if (cluster.count > 1) {
          const allLats = cluster.properties.map(p => getPropertyCoordinates(p).lat)
          const allLngs = cluster.properties.map(p => getPropertyCoordinates(p).lng)
          cluster.center.lat = allLats.reduce((sum, lat) => sum + lat, 0) / allLats.length
          cluster.center.lng = allLngs.reduce((sum, lng) => sum + lng, 0) / allLngs.length
        }

        // Determine cluster size based on count and zoom
        if (cluster.count >= 100) cluster.size = "xlarge"
        else if (cluster.count >= 50) cluster.size = "large"
        else if (cluster.count >= 10) cluster.size = "medium"
        else cluster.size = "small"

        clusters.push(cluster)
      } else {
        // If cluster is too small, add properties as individual markers
        cluster.properties.forEach(property => {
          const propCoords = getPropertyCoordinates(property)
          clusters.push({
            center: propCoords,
            properties: [property],
            bounds: {
              north: propCoords.lat,
              south: propCoords.lat,
              east: propCoords.lng,
              west: propCoords.lng,
            },
            size: "small",
            count: 1
          })
        })
      }
    })
  })

  // Calculate representative price for each cluster (prioritize sale over rent)
  clusters.forEach(cluster => {
    const priceData = cluster.properties.map((property: any) => {
      const saleHigh = parseFloat(property.매매_최고가_억원 || '0')
      const saleLow = parseFloat(property.매매_최저가_억원 || '0')
      const rentHigh = parseFloat(property.전세_최고가_억원 || '0')
      const rentLow = parseFloat(property.전세_최저가_억원 || '0')
      
      // Prioritize sale price, use average of high/low if both exist
      if (saleHigh > 0 || saleLow > 0) {
        const avgSale = saleHigh > 0 && saleLow > 0 ? (saleHigh + saleLow) / 2 : (saleHigh || saleLow)
        return { price: avgSale, type: 'sale' }
      } else if (rentHigh > 0 || rentLow > 0) {
        const avgRent = rentHigh > 0 && rentLow > 0 ? (rentHigh + rentLow) / 2 : (rentHigh || rentLow)
        return { price: avgRent, type: 'rent' }
      }
      return { price: 0, type: 'none' }
    }).filter(item => item.price > 0)
    
    if (priceData.length > 0) {
      // Prefer sale prices for average calculation
      const saleOnlyPrices = priceData.filter(item => item.type === 'sale').map(item => item.price)
      if (saleOnlyPrices.length > 0) {
        cluster.averagePrice = saleOnlyPrices.reduce((sum, price) => sum + price, 0) / saleOnlyPrices.length
      } else {
        // Use rent prices if no sale prices available
        cluster.averagePrice = priceData.reduce((sum, item) => sum + item.price, 0) / priceData.length
      }
    }
  })

  return clusters
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
export function createDetailedMarkerContent(property: any): string {
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
    const saleHigh = property.매매_최고가_억원;
    const saleLow = property.매매_최저가_억원;
    const rentHigh = property.전세_최고가_억원;
    const rentLow = property.전세_최저가_억원;
    const monthlyHigh = property.월세_최고가_억원;
    const monthlyLow = property.월세_최저가_억원;
    
    // Show price ranges when available, prioritize sales > jeonse > monthly
    if (saleHigh && saleHigh !== '' && saleHigh !== '0') {
      primaryPrice = saleLow !== saleHigh ? `${saleLow}~${saleHigh}억` : `${saleHigh}억`;
      priceType = '매매';
    } else if (rentHigh && rentHigh !== '' && rentHigh !== '0') {
      primaryPrice = rentLow !== rentHigh ? `${rentLow}~${rentHigh}억` : `${rentHigh}억`;
      priceType = '전세';
    } else if (monthlyHigh && monthlyHigh !== '' && monthlyHigh !== '0') {
      primaryPrice = monthlyLow !== monthlyHigh ? `${monthlyLow}~${monthlyHigh}만` : `${monthlyHigh}만`;
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

// Create hogangnono-style cluster marker content
export function createClusterMarkerContent(cluster: Cluster, style: any): string {
  const sizeMap: Record<string, { width: number; height: number }> = {
    small: { width: 24, height: 24 },
    medium: { width: 32, height: 32 },
    large: { width: 40, height: 40 },
    xlarge: { width: 48, height: 48 }
  };
  
  const size = sizeMap[style.size as keyof typeof sizeMap] || sizeMap.medium;
  
  // Hogangnono-style dong cluster display (only for far zoom)
  if (cluster.count > 1) {
    const avgPriceText = cluster.averagePrice 
      ? `${cluster.averagePrice.toFixed(1)}억` 
      : '정보없음';
    
    const displayName = cluster.dongName || '알 수 없음';
    
    return `
      <div style="
        background: ${style.backgroundColor};
        color: ${style.color};
        padding: 12px 16px;
        border-radius: 8px;
        border: 2px solid ${style.borderColor};
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        cursor: pointer;
        font-weight: 600;
        font-size: 12px;
        text-align: center;
        min-width: 100px;
        max-width: 140px;
        transition: all 0.2s ease;
      " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
        <div style="font-size: 11px; font-weight: 700; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          ${displayName}
        </div>
        <div style="font-size: 14px; font-weight: 700;">
          ${avgPriceText}
        </div>
      </div>
    `;
  }
  
  // Simple circle for regular clusters
  return `
    <div style="
      background: ${style.backgroundColor};
      width: ${size.width}px;
      height: ${size.height}px;
      border-radius: 50%;
      border: 2px solid ${style.borderColor};
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      color: ${style.color};
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
