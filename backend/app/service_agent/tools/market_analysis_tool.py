"""
시장 동향 및 가격 적정성 분석 Tool
부동산 시세 데이터를 분석하여 가격 적정성과 시장 동향 파악
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class MarketAnalysisTool:
    """
    시장 분석 도구
    부동산 시세, 거래 동향, 가격 적정성 분석
    """

    def __init__(self, market_search_tool=None, llm_service=None):
        """
        초기화

        Args:
            market_search_tool: 시장 데이터 검색 도구 (선택적)
            llm_service: LLM 서비스 (선택적)
        """
        self.market_search_tool = market_search_tool
        self.llm_service = llm_service
        self.name = "market_analysis"

        # 분석 기준
        self.price_bands = {
            "very_low": -0.15,   # 시세 대비 -15% 이하
            "low": -0.05,        # 시세 대비 -5% ~ -15%
            "fair": 0.05,        # 시세 대비 -5% ~ +5%
            "high": 0.15,        # 시세 대비 +5% ~ +15%
            "very_high": 999     # 시세 대비 +15% 이상
        }

        logger.info("MarketAnalysisTool initialized")

    async def execute(
        self,
        property_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        시장 분석 실행

        Args:
            property_data: 분석할 부동산 정보
            market_data: 시장 데이터 (선택적, 없으면 자체 검색)
            analysis_type: 분석 유형 (quick/comprehensive)

        Returns:
            분석 결과 딕셔너리
        """
        try:
            logger.info(f"Analyzing market for {property_data.get('address', 'property')}")

            # 1. 시장 데이터 확보
            if not market_data and self.market_search_tool:
                market_data = await self._search_market_data(property_data)

            # 2. 가격 적정성 분석
            price_analysis = self._analyze_price_fairness(property_data, market_data)

            # 3. 시장 동향 분석
            market_trend = self._analyze_market_trend(market_data)

            # 4. 경쟁력 분석
            competitiveness = self._analyze_competitiveness(property_data, market_data)

            # 5. 지역 특성 분석
            regional_analysis = self._analyze_regional_factors(property_data, market_data)

            # 6. 투자 가치 평가
            investment_value = self._evaluate_investment_value(
                price_analysis, market_trend, regional_analysis
            )

            # 7. LLM 종합 분석 (가능한 경우)
            comprehensive_insight = None
            if self.llm_service and analysis_type == "comprehensive":
                comprehensive_insight = await self._llm_market_insight(
                    property_data, market_data, price_analysis, market_trend
                )

            return {
                "status": "success",
                "property_address": property_data.get("address"),
                "analysis_type": analysis_type,
                "price_analysis": price_analysis,
                "market_trend": market_trend,
                "competitiveness": competitiveness,
                "regional_factors": regional_analysis,
                "investment_value": investment_value,
                "comprehensive_insight": comprehensive_insight,
                "confidence": self._calculate_confidence(market_data),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "property_address": property_data.get("address"),
                "timestamp": datetime.now().isoformat()
            }

    async def _search_market_data(self, property_data: Dict) -> Dict:
        """시장 데이터 검색"""
        try:
            # 검색 파라미터 구성
            search_params = {
                "region": property_data.get("region") or property_data.get("address", "").split()[0],
                "property_type": property_data.get("type", "apartment"),
                "size_range": self._get_size_range(property_data.get("size")),
                "period": "6months"
            }

            results = await self.market_search_tool.search(**search_params)

            return {
                "recent_transactions": results.get("transactions", []),
                "current_listings": results.get("listings", []),
                "price_history": results.get("price_history", []),
                "regional_stats": results.get("regional_stats", {})
            }
        except Exception as e:
            logger.error(f"Market data search failed: {e}")
            return {}

    def _analyze_price_fairness(
        self,
        property_data: Dict,
        market_data: Dict
    ) -> Dict[str, Any]:
        """가격 적정성 분석"""
        target_price = property_data.get("price", 0)
        if not target_price:
            return {"status": "no_price_data"}

        # 유사 매물 가격 수집
        similar_prices = []

        # 최근 거래 가격
        for trans in market_data.get("recent_transactions", [])[:20]:
            if self._is_similar_property(property_data, trans):
                similar_prices.append(trans.get("price", 0))

        # 현재 매물 가격
        for listing in market_data.get("current_listings", [])[:20]:
            if self._is_similar_property(property_data, listing):
                similar_prices.append(listing.get("price", 0))

        if not similar_prices:
            return {"status": "insufficient_data"}

        # 통계 분석
        avg_price = statistics.mean(similar_prices)
        median_price = statistics.median(similar_prices)
        std_dev = statistics.stdev(similar_prices) if len(similar_prices) > 1 else 0

        # 가격 차이 계산
        diff_from_avg = (target_price - avg_price) / avg_price if avg_price else 0
        diff_from_median = (target_price - median_price) / median_price if median_price else 0

        # 가격 평가
        price_level = self._get_price_level(diff_from_avg)

        return {
            "target_price": target_price,
            "market_average": round(avg_price),
            "market_median": round(median_price),
            "standard_deviation": round(std_dev),
            "price_difference_pct": round(diff_from_avg * 100, 2),
            "price_level": price_level,
            "sample_size": len(similar_prices),
            "recommendation": self._get_price_recommendation(price_level, diff_from_avg),
            "fair_price_range": {
                "min": round(avg_price * 0.95),
                "max": round(avg_price * 1.05)
            }
        }

    def _analyze_market_trend(self, market_data: Dict) -> Dict[str, Any]:
        """시장 동향 분석"""
        price_history = market_data.get("price_history", [])
        if not price_history:
            return {"status": "no_history_data"}

        # 시간대별 가격 추이
        monthly_prices = {}
        for record in price_history:
            month = record.get("date", "")[:7]  # YYYY-MM
            if month not in monthly_prices:
                monthly_prices[month] = []
            monthly_prices[month].append(record.get("price", 0))

        # 월별 평균 계산
        monthly_averages = {
            month: statistics.mean(prices)
            for month, prices in monthly_prices.items()
        }

        if len(monthly_averages) < 2:
            return {"status": "insufficient_history"}

        # 트렌드 계산
        sorted_months = sorted(monthly_averages.keys())
        recent_avg = monthly_averages[sorted_months[-1]]
        prev_avg = monthly_averages[sorted_months[-2]]
        oldest_avg = monthly_averages[sorted_months[0]]

        # 변화율 계산
        monthly_change = (recent_avg - prev_avg) / prev_avg if prev_avg else 0
        total_change = (recent_avg - oldest_avg) / oldest_avg if oldest_avg else 0

        # 트렌드 판단
        if monthly_change > 0.02:
            trend = "rising_fast"
        elif monthly_change > 0.005:
            trend = "rising"
        elif monthly_change < -0.02:
            trend = "falling_fast"
        elif monthly_change < -0.005:
            trend = "falling"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "monthly_change_pct": round(monthly_change * 100, 2),
            "total_change_pct": round(total_change * 100, 2),
            "period_months": len(monthly_averages),
            "volatility": self._calculate_volatility(list(monthly_averages.values())),
            "prediction": self._predict_trend(trend, monthly_change),
            "monthly_averages": monthly_averages
        }

    def _analyze_competitiveness(
        self,
        property_data: Dict,
        market_data: Dict
    ) -> Dict[str, Any]:
        """경쟁력 분석"""
        score = 50  # 기본 점수
        factors = []

        # 가격 경쟁력
        if property_data.get("price"):
            listings = market_data.get("current_listings", [])
            cheaper_count = sum(
                1 for l in listings
                if l.get("price", float('inf')) < property_data["price"]
            )
            if listings:
                price_rank = (cheaper_count / len(listings)) * 100
                score += (50 - price_rank) / 2
                factors.append(f"가격 순위: 상위 {100-price_rank:.1f}%")

        # 위치 경쟁력
        if property_data.get("distance_to_subway"):
            if property_data["distance_to_subway"] < 500:
                score += 10
                factors.append("역세권 (500m 이내)")
            elif property_data["distance_to_subway"] < 1000:
                score += 5
                factors.append("준역세권 (1km 이내)")

        # 층수 경쟁력
        if property_data.get("floor"):
            floor = property_data["floor"]
            if 5 <= floor <= 15:
                score += 5
                factors.append(f"선호 층수 ({floor}층)")

        # 향 경쟁력
        if property_data.get("direction"):
            if property_data["direction"] in ["남향", "남동향", "남서향"]:
                score += 5
                factors.append(f"우수한 향 ({property_data['direction']})")

        return {
            "competitiveness_score": min(100, max(0, score)),
            "factors": factors,
            "grade": self._get_grade(score),
            "strengths": [f for f in factors if "우수" in f or "역세권" in f],
            "weaknesses": [f for f in factors if "하위" in f]
        }

    def _analyze_regional_factors(
        self,
        property_data: Dict,
        market_data: Dict
    ) -> Dict[str, Any]:
        """지역 특성 분석"""
        regional_stats = market_data.get("regional_stats", {})

        factors = {
            "infrastructure": self._evaluate_infrastructure(property_data),
            "education": self._evaluate_education(property_data, regional_stats),
            "commercial": self._evaluate_commercial(property_data),
            "transportation": self._evaluate_transportation(property_data),
            "development": self._evaluate_development(regional_stats)
        }

        # 종합 점수
        total_score = sum(f.get("score", 50) for f in factors.values()) / len(factors)

        return {
            "total_score": round(total_score, 1),
            "factors": factors,
            "highlights": self._get_regional_highlights(factors),
            "concerns": self._get_regional_concerns(factors)
        }

    def _evaluate_investment_value(
        self,
        price_analysis: Dict,
        market_trend: Dict,
        regional_analysis: Dict
    ) -> Dict[str, Any]:
        """투자 가치 평가"""
        score = 50

        # 가격 적정성 반영
        if price_analysis.get("price_level") == "fair":
            score += 10
        elif price_analysis.get("price_level") == "low":
            score += 15
        elif price_analysis.get("price_level") == "very_low":
            score += 20
        elif price_analysis.get("price_level") == "high":
            score -= 10
        elif price_analysis.get("price_level") == "very_high":
            score -= 20

        # 시장 트렌드 반영
        if market_trend.get("trend") == "rising_fast":
            score += 15
        elif market_trend.get("trend") == "rising":
            score += 10
        elif market_trend.get("trend") == "falling":
            score -= 10
        elif market_trend.get("trend") == "falling_fast":
            score -= 15

        # 지역 특성 반영
        regional_score = regional_analysis.get("total_score", 50)
        score += (regional_score - 50) / 2

        # 투자 등급 결정
        if score >= 80:
            grade = "excellent"
            recommendation = "매우 좋은 투자 기회입니다."
        elif score >= 65:
            grade = "good"
            recommendation = "좋은 투자 기회입니다."
        elif score >= 50:
            grade = "fair"
            recommendation = "적정한 투자입니다."
        elif score >= 35:
            grade = "caution"
            recommendation = "신중한 검토가 필요합니다."
        else:
            grade = "poor"
            recommendation = "투자를 재검토하세요."

        return {
            "investment_score": round(score, 1),
            "grade": grade,
            "recommendation": recommendation,
            "key_factors": {
                "price_advantage": price_analysis.get("price_level") in ["low", "very_low"],
                "growth_potential": market_trend.get("trend") in ["rising", "rising_fast"],
                "location_quality": regional_analysis.get("total_score", 50) > 65
            }
        }

    async def _llm_market_insight(
        self,
        property_data: Dict,
        market_data: Dict,
        price_analysis: Dict,
        market_trend: Dict
    ) -> Dict[str, Any]:
        """LLM을 통한 종합 인사이트"""
        if not self.llm_service:
            return None

        try:
            prompt = f"""다음 부동산의 시장 분석 결과를 바탕으로 종합적인 인사이트를 제공해주세요:

물건 정보:
- 주소: {property_data.get('address')}
- 가격: {property_data.get('price')}
- 면적: {property_data.get('size')}

가격 분석:
- 시세 대비: {price_analysis.get('price_difference_pct')}%
- 평가: {price_analysis.get('price_level')}

시장 동향:
- 트렌드: {market_trend.get('trend')}
- 월간 변화: {market_trend.get('monthly_change_pct')}%

다음 관점에서 분석해주세요:
1. 현재 가격의 적정성
2. 향후 가격 전망
3. 투자 또는 실거주 관점에서의 장단점
4. 주의사항 및 추천사항
"""

            response = await self.llm_service.complete_async(
                prompt_name="insight_generation",
                variables={"prompt": prompt},
                temperature=0.3
            )

            return {
                "insight": response,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            return None

    def _is_similar_property(self, target: Dict, comparison: Dict) -> bool:
        """유사 매물 판단"""
        # 면적 비교 (±20%)
        if target.get("size") and comparison.get("size"):
            size_diff = abs(target["size"] - comparison["size"]) / target["size"]
            if size_diff > 0.2:
                return False

        # 타입 비교
        if target.get("type") and comparison.get("type"):
            if target["type"] != comparison["type"]:
                return False

        return True

    def _get_size_range(self, size: Optional[float]) -> tuple:
        """면적 범위 계산"""
        if not size:
            return (0, 999)
        return (size * 0.8, size * 1.2)

    def _get_price_level(self, diff_pct: float) -> str:
        """가격 수준 판단"""
        if diff_pct < -0.15:
            return "very_low"
        elif diff_pct < -0.05:
            return "low"
        elif diff_pct < 0.05:
            return "fair"
        elif diff_pct < 0.15:
            return "high"
        else:
            return "very_high"

    def _get_price_recommendation(self, level: str, diff_pct: float) -> str:
        """가격 추천"""
        recommendations = {
            "very_low": "시세보다 매우 저렴합니다. 숨은 하자가 없는지 확인하세요.",
            "low": "시세보다 저렴한 좋은 기회입니다.",
            "fair": "적정 가격입니다.",
            "high": "시세보다 다소 높습니다. 협상을 시도하세요.",
            "very_high": "시세보다 과도하게 높습니다. 다른 매물을 검토하세요."
        }
        return recommendations.get(level, "추가 검토가 필요합니다.")

    def _calculate_volatility(self, prices: List[float]) -> str:
        """변동성 계산"""
        if not prices:
            return "unknown"

        std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
        mean = statistics.mean(prices)
        cv = (std_dev / mean) if mean else 0

        if cv < 0.05:
            return "low"
        elif cv < 0.15:
            return "moderate"
        else:
            return "high"

    def _predict_trend(self, trend: str, change_rate: float) -> str:
        """트렌드 예측"""
        predictions = {
            "rising_fast": "단기간 추가 상승 가능성이 높습니다.",
            "rising": "완만한 상승세가 지속될 것으로 예상됩니다.",
            "stable": "현재 수준을 유지할 가능성이 높습니다.",
            "falling": "하락세가 지속될 수 있으니 주의가 필요합니다.",
            "falling_fast": "급격한 하락 중이므로 매수를 보류하는 것이 좋습니다."
        }
        return predictions.get(trend, "추세 판단이 어렵습니다.")

    def _get_grade(self, score: float) -> str:
        """등급 판정"""
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"

    def _evaluate_infrastructure(self, property_data: Dict) -> Dict:
        """인프라 평가"""
        score = 50
        factors = []

        if property_data.get("nearby_facilities"):
            facilities = property_data["nearby_facilities"]
            if "병원" in facilities:
                score += 5
                factors.append("의료시설 접근성 우수")
            if "대형마트" in facilities:
                score += 5
                factors.append("쇼핑 편의성 우수")

        return {"score": score, "factors": factors}

    def _evaluate_education(self, property_data: Dict, regional_stats: Dict) -> Dict:
        """교육 환경 평가"""
        score = 50
        factors = []

        if regional_stats.get("school_score"):
            school_score = regional_stats["school_score"]
            if school_score > 80:
                score += 15
                factors.append("우수한 학군")
            elif school_score > 60:
                score += 5
                factors.append("양호한 학군")

        return {"score": score, "factors": factors}

    def _evaluate_commercial(self, property_data: Dict) -> Dict:
        """상권 평가"""
        return {"score": 55, "factors": ["활성화된 상권"]}

    def _evaluate_transportation(self, property_data: Dict) -> Dict:
        """교통 평가"""
        score = 50
        factors = []

        if property_data.get("distance_to_subway"):
            if property_data["distance_to_subway"] < 500:
                score += 15
                factors.append("역세권")

        return {"score": score, "factors": factors}

    def _evaluate_development(self, regional_stats: Dict) -> Dict:
        """개발 호재 평가"""
        score = 50
        factors = []

        if regional_stats.get("development_plans"):
            score += 10
            factors.append("개발 계획 있음")

        return {"score": score, "factors": factors}

    def _get_regional_highlights(self, factors: Dict) -> List[str]:
        """지역 장점"""
        highlights = []
        for category, data in factors.items():
            if data.get("score", 0) > 60:
                highlights.extend(data.get("factors", []))
        return highlights[:3]

    def _get_regional_concerns(self, factors: Dict) -> List[str]:
        """지역 단점"""
        concerns = []
        for category, data in factors.items():
            if data.get("score", 0) < 40:
                concerns.append(f"{category} 부족")
        return concerns[:3]

    def _calculate_confidence(self, market_data: Dict) -> float:
        """신뢰도 계산"""
        data_points = 0
        data_points += len(market_data.get("recent_transactions", []))
        data_points += len(market_data.get("current_listings", []))
        data_points += len(market_data.get("price_history", []))

        if data_points > 50:
            return 0.95
        elif data_points > 20:
            return 0.85
        elif data_points > 10:
            return 0.70
        else:
            return 0.50


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_market_analysis():
        tool = MarketAnalysisTool()

        # 테스트 데이터
        property_info = {
            "address": "서울시 강남구 역삼동 123-45",
            "type": "apartment",
            "size": 84.5,
            "price": 1500000000,  # 15억
            "floor": 10,
            "direction": "남향",
            "distance_to_subway": 300
        }

        mock_market_data = {
            "recent_transactions": [
                {"price": 1450000000, "size": 84, "date": "2024-01"},
                {"price": 1480000000, "size": 85, "date": "2024-01"},
                {"price": 1520000000, "size": 84, "date": "2024-02"}
            ],
            "current_listings": [
                {"price": 1550000000, "size": 84},
                {"price": 1480000000, "size": 85}
            ],
            "price_history": [
                {"price": 1400000000, "date": "2023-08"},
                {"price": 1420000000, "date": "2023-09"},
                {"price": 1450000000, "date": "2023-10"}
            ]
        }

        result = await tool.execute(
            property_data=property_info,
            market_data=mock_market_data
        )

        print("=== Market Analysis Result ===")
        print(f"Status: {result['status']}")
        print(f"\nPrice Analysis:")
        print(f"  Target: {result['price_analysis'].get('target_price'):,}원")
        print(f"  Market Avg: {result['price_analysis'].get('market_average'):,}원")
        print(f"  Difference: {result['price_analysis'].get('price_difference_pct')}%")
        print(f"  Level: {result['price_analysis'].get('price_level')}")

        print(f"\nMarket Trend:")
        print(f"  Trend: {result['market_trend'].get('trend')}")
        print(f"  Monthly Change: {result['market_trend'].get('monthly_change_pct')}%")

        print(f"\nInvestment Value:")
        print(f"  Score: {result['investment_value'].get('investment_score')}")
        print(f"  Grade: {result['investment_value'].get('grade')}")
        print(f"  Recommendation: {result['investment_value'].get('recommendation')}")

    asyncio.run(test_market_analysis())