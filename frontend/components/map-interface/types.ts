/**
 * Shared types for map-interface components
 */

export interface PropertyData {
  name: string
  gu: string
  dong: string
  // 가격 정보 - 억원 표시용 (포맷된 문자열)
  sale_min_price_eok?: string
  sale_max_price_eok?: string
  jeonse_min_price_eok?: string
  jeonse_max_price_eok?: string
  rent_min_price_eok?: string
  rent_max_price_eok?: string
  // 가격 정보 - Raw values in 만원 units (for calculations)
  sale_min_price?: string
  sale_max_price?: string
  jeonse_min_price?: string
  jeonse_max_price?: string
  rent_min_price?: string
  rent_max_price?: string
  summary: string
  total_article_count: string
  area_summary: string
  total_households: string
  total_buildings: string
  completion_date: string
  latitude?: number
  longitude?: number
  type?: "office" | "residential" | "dong" | "gu"  // 집계 데이터 타입 추가
  property_type?: string  // 부동산 유형 (아파트, 오피스텔, 빌라, 단독/다가구, 동 최저가, 구 최저가 등)
  count?: number  // 집계 데이터의 매물 개수
  // 주변 시설 정보
  nearby_subway_stations?: string  // JSON 문자열
  nearby_schools?: string  // JSON 문자열
  nearby_marts?: string  // JSON 문자열
}
