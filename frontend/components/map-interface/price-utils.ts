/**
 * Price utility functions for real estate
 * Eliminates 10+ duplications of price conversion logic
 */

/**
 * Convert price from 만원 (man-won) to 억원 (eok-won)
 * @param priceInManwon - Price in 만원 units
 * @returns Price in 억원 units
 * @example convertManwonToEok(50000) => 5 (5억원)
 */
export function convertManwonToEok(priceInManwon: number): number {
  return priceInManwon / 10000
}

/**
 * Format price in 억원 with appropriate display
 * @param priceInManwon - Price in 만원 units
 * @returns Formatted string like "5억" or "1.5억" or "5000만원"
 * @example formatPriceInEok(50000) => "5억"
 * @example formatPriceInEok(15000) => "1.5억"
 * @example formatPriceInEok(5000) => "5,000만원"
 */
export function formatPriceInEok(priceInManwon: number): string {
  if (priceInManwon >= 10000) {
    const eok = priceInManwon / 10000
    return eok % 1 === 0 ? `${Math.round(eok)}억` : `${eok.toFixed(1)}억`
  }
  return `${Math.round(priceInManwon).toLocaleString()}만원`
}

/**
 * Parse price string to number (handles both string and number inputs)
 * @param price - Price as string or number
 * @returns Parsed number or 0 if invalid
 */
export function parsePrice(price: string | number | undefined): number {
  if (typeof price === 'number') return price
  if (!price || price === '' || price === '0') return 0
  return parseFloat(price)
}

/**
 * Check if price is valid (greater than 0)
 * @param price - Price in any format
 * @returns true if price is valid
 */
export function isPriceValid(price: string | number | undefined): boolean {
  const parsed = parsePrice(price)
  return parsed > 0
}

/**
 * Get price in 억원 from 만원 string
 * @param priceInManwon - Price string in 만원
 * @returns Price in 억원, or 0 if invalid
 */
export function getPriceInEok(priceInManwon: string | undefined): number {
  const parsed = parsePrice(priceInManwon)
  return parsed > 0 ? convertManwonToEok(parsed) : 0
}

/**
 * Format price range for display
 * @param minPrice - Minimum price in 만원
 * @param maxPrice - Maximum price in 만원
 * @returns Formatted range like "1억 ~ 2억" or "5000만원 ~ 1억"
 */
export function formatPriceRange(minPrice: string | number, maxPrice: string | number): string {
  const min = parsePrice(minPrice)
  const max = parsePrice(maxPrice)

  if (min === 0 && max === 0) return "-"
  if (min === 0) return formatPriceInEok(max)
  if (max === 0) return formatPriceInEok(min)

  const minFormatted = formatPriceInEok(min)
  const maxFormatted = formatPriceInEok(max)

  return `${minFormatted} ~ ${maxFormatted}`
}

/**
 * Check if price is within range (in 억원)
 * @param priceInManwon - Price to check (in 만원)
 * @param minEok - Minimum range in 억원
 * @param maxEok - Maximum range in 억원
 * @returns true if price is within range
 */
export function isPriceInRange(
  priceInManwon: string | number | undefined,
  minEok: number,
  maxEok: number
): boolean {
  const priceEok = getPriceInEok(priceInManwon as string)
  return priceEok >= minEok && priceEok <= maxEok
}
