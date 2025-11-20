/**
 * Marker utility functions for Kakao Map
 * Extracts HTML template generation logic from setupPropertyMarkers
 */

import type { PropertyData } from './types'
import { formatPriceInEok, parsePrice } from './price-utils'

/**
 * Get marker color based on transaction type
 */
export function getMarkerColor(transactionType: string): string {
  switch (transactionType) {
    case '매매':
      return '#EF4444' // Vibrant red for sale
    case '전세':
      return '#3B82F6' // Bright blue for jeonse
    case '월세':
      return '#10B981' // Fresh green for monthly
    default:
      return '#3182f6' // Default blue
  }
}

/**
 * Get icon text for transaction type
 */
export function getIconText(transactionType: string): string {
  switch (transactionType) {
    case '매매':
      return '매'
    case '전세':
      return '전'
    case '월세':
      return '월'
    default:
      return '?'
  }
}

/**
 * Determine price and transaction type for property marker
 */
export function getPropertyMarkerData(
  property: PropertyData,
  transactionFilter: string
): { priceText: string; markerColor: string; iconText: string } {
  const isAggregated = property.property_type === "동 최저가" || property.property_type === "구 최저가"

  // Helper to check if price string is valid
  const isValidEokPrice = (price: any) => price && price !== '' && price !== '0'
  const isValidPrice = (price: any) => price && price !== '' && price !== '0' && parseFloat(price) > 0

  let priceText = ''
  let markerColor = '#3182f6'
  let iconText = ''

  // 집계 데이터(동/구 최저가)의 경우
  if (isAggregated) {
    const saleEok = property.sale_max_price_eok
    const jeonseEok = property.jeonse_max_price_eok
    const rentEok = property.rent_max_price_eok
    const aggregateIcon = property.property_type === "동 최저가" ? "동" : "구"

    // Determine by filter or priority
    if (transactionFilter === "매매" && isValidEokPrice(saleEok)) {
      priceText = saleEok
      markerColor = getMarkerColor('매매')
      iconText = aggregateIcon
    } else if (transactionFilter === "전세" && isValidEokPrice(jeonseEok)) {
      priceText = jeonseEok
      markerColor = getMarkerColor('전세')
      iconText = aggregateIcon
    } else if (transactionFilter === "월세" && isValidEokPrice(rentEok)) {
      priceText = rentEok
      markerColor = getMarkerColor('월세')
      iconText = aggregateIcon
    } else if (isValidEokPrice(saleEok)) {
      priceText = saleEok
      markerColor = getMarkerColor('매매')
      iconText = aggregateIcon
    } else if (isValidEokPrice(jeonseEok)) {
      priceText = jeonseEok
      markerColor = getMarkerColor('전세')
      iconText = aggregateIcon
    } else if (isValidEokPrice(rentEok)) {
      priceText = rentEok
      markerColor = getMarkerColor('월세')
      iconText = aggregateIcon
    } else {
      priceText = property.name || '-'
      iconText = aggregateIcon
    }
  } else {
    // 개별 매물 데이터 처리
    const saleHigh = property.sale_max_price
    const rentHigh = property.jeonse_max_price
    const monthlyHigh = property.rent_max_price

    // Determine by filter or priority
    if (transactionFilter === "매매") {
      if (isValidPrice(saleHigh)) {
        const price = parsePrice(saleHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('매매')
        iconText = getIconText('매매')
      } else {
        // Filter is Sale but no Sale price -> Hide marker
        priceText = ''
        iconText = ''
        markerColor = ''
      }
    } else if (transactionFilter === "전세") {
      if (isValidPrice(rentHigh)) {
        const price = parsePrice(rentHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('전세')
        iconText = getIconText('전세')
      } else {
        priceText = ''
        iconText = ''
        markerColor = ''
      }
    } else if (transactionFilter === "월세") {
      if (isValidPrice(monthlyHigh)) {
        const price = parsePrice(monthlyHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('월세')
        iconText = getIconText('월세')
      } else {
        priceText = ''
        iconText = ''
        markerColor = ''
      }
    } else {
      // "전체" filter - use priority
      if (isValidPrice(saleHigh)) {
        const price = parsePrice(saleHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('매매')
        iconText = getIconText('매매')
      } else if (isValidPrice(rentHigh)) {
        const price = parsePrice(rentHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('전세')
        iconText = getIconText('전세')
      } else if (isValidPrice(monthlyHigh)) {
        const price = parsePrice(monthlyHigh)
        priceText = formatPriceInEok(price)
        markerColor = getMarkerColor('월세')
        iconText = getIconText('월세')
      } else {
        priceText = ''
        iconText = ''
        markerColor = ''
      }
    }
  }

  return { priceText, markerColor, iconText }
}

/**
 * Create property marker HTML content
 */
export function createPropertyMarkerContent(
  property: PropertyData,
  transactionFilter: string
): string {
  const { priceText, markerColor, iconText } = getPropertyMarkerData(property, transactionFilter)

  // If no valid price/color (hidden), return empty string to prevent rendering
  if (!priceText || !markerColor || priceText === '-' || priceText === '') {
    return ''
  }

  const isApartment = property.property_type === "아파트" || property.property_type === "APT"
  const propertyTypeBadge = !isApartment && property.property_type ? property.property_type : ''

  return `
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
        display: flex;
        flex-direction: column;
        align-items: center;
      ">
        <span>${priceText}</span>
        ${propertyTypeBadge ? `<span style="font-size: 9px; font-weight: 500; opacity: 0.9; border-top: 1px solid rgba(255,255,255,0.3); width: 100%; text-align: center; margin-top: 1px; padding-top: 1px;">${propertyTypeBadge}</span>` : ''}
      </div>
    </div>
  `
}

/**
 * Calculate cluster average price
 */
export function calculateClusterAveragePrice(
  properties: PropertyData[],
  transactionFilter: string
): number {
  let validPrices: number[] = []

  if (transactionFilter === '매매') {
    validPrices = properties
      .map(p => parsePrice(p.sale_max_price))
      .filter(p => p > 0)
  } else if (transactionFilter === '전세') {
    validPrices = properties
      .map(p => parsePrice(p.jeonse_max_price))
      .filter(p => p > 0)
  } else if (transactionFilter === '월세') {
    validPrices = properties
      .map(p => parsePrice(p.rent_max_price))
      .filter(p => p > 0)
  } else {
    // "전체" - 매매 -> 전세 -> 월세 순으로 유효한 가격 찾기
    const salePrices = properties.map(p => parsePrice(p.sale_max_price)).filter(p => p > 0)
    const jeonsePrices = properties.map(p => parsePrice(p.jeonse_max_price)).filter(p => p > 0)
    const rentPrices = properties.map(p => parsePrice(p.rent_max_price)).filter(p => p > 0)

    if (salePrices.length > 0) validPrices = salePrices
    else if (jeonsePrices.length > 0) validPrices = jeonsePrices
    else if (rentPrices.length > 0) validPrices = rentPrices
  }

  if (validPrices.length > 0) {
    return validPrices.reduce((a, b) => a + b, 0) / validPrices.length
  }

  return 0
}
