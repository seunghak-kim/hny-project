"""
Analysis Tools for AnalysisAgent
=================================
Provides various analysis capabilities for real estate data

This file maintains compatibility with existing code while also supporting new tools.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import statistics
import random

# Import new analysis tools for enhanced functionality
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool as NewMarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool

logger = logging.getLogger(__name__)


class BaseAnalysisTool:
    """Base class for all analysis tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"analysis.{name}")

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main analysis method to be implemented by subclasses"""
        raise NotImplementedError

    async def execute(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute analysis with error handling"""
        try:
            self.logger.info(f"Executing {self.name} analysis")
            result = await self.analyze(data, params)
            result["tool_name"] = self.name
            result["timestamp"] = datetime.now().isoformat()
            result["status"] = "success"
            return result
        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}")
            return {
                "status": "error",
                "tool_name": self.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class MarketAnalyzer(BaseAnalysisTool):
    """Analyzes overall market conditions"""

    def __init__(self):
        super().__init__(
            name="market_analyzer",
            description="Analyzes market conditions including supply/demand, pricing trends"
        )

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze market conditions"""
        # Extract relevant data
        listings = []
        for source, items in data.items():
            if isinstance(items, list):
                listings.extend(items)

        if not listings:
            return {
                "analysis": "No data available for market analysis",
                "metrics": {}
            }

        # Calculate market metrics (using mock calculations)
        prices = []
        for listing in listings:
            if isinstance(listing, dict) and "price" in listing:
                try:
                    # Extract numeric price (handle various formats)
                    price_str = listing["price"]
                    if isinstance(price_str, str):
                        price_num = float(price_str.replace("억", "").replace(",", "").strip())
                        prices.append(price_num)
                except:
                    continue

        # Calculate statistics
        if prices:
            avg_price = statistics.mean(prices)
            median_price = statistics.median(prices)
            price_std = statistics.stdev(prices) if len(prices) > 1 else 0

            # Market indicators (mock)
            supply_demand_ratio = random.uniform(0.8, 1.2)
            market_heat_index = min(100, (avg_price / 10) + random.uniform(20, 40))
            price_volatility = (price_std / avg_price * 100) if avg_price > 0 else 0
        else:
            avg_price = median_price = price_std = 0
            supply_demand_ratio = 1.0
            market_heat_index = 50
            price_volatility = 0

        return {
            "analysis": "Market analysis completed",
            "metrics": {
                "average_price": f"{avg_price:.1f}억" if avg_price else "N/A",
                "median_price": f"{median_price:.1f}억" if median_price else "N/A",
                "price_volatility": f"{price_volatility:.1f}%",
                "supply_demand_ratio": round(supply_demand_ratio, 2),
                "market_heat_index": round(market_heat_index, 1),
                "total_listings": len(listings),
                "price_range": {
                    "min": f"{min(prices):.1f}억" if prices else "N/A",
                    "max": f"{max(prices):.1f}억" if prices else "N/A"
                }
            },
            "market_conditions": {
                "overall": "활발" if market_heat_index > 70 else "보통" if market_heat_index > 40 else "침체",
                "supply_status": "공급 과잉" if supply_demand_ratio < 0.9 else "균형" if supply_demand_ratio < 1.1 else "공급 부족",
                "price_trend": "상승" if random.random() > 0.5 else "하락"
            }
        }


class TrendAnalyzer(BaseAnalysisTool):
    """Analyzes price and transaction trends"""

    def __init__(self):
        super().__init__(
            name="trend_analyzer",
            description="Analyzes historical trends and patterns in real estate data"
        )

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze trends in the data"""
        # Mock trend analysis
        trend_period = params.get("period", "3months") if params else "3months"

        # Generate mock trend data
        price_trend = random.uniform(-5, 10)  # Percentage change
        volume_trend = random.uniform(-10, 15)
        days_on_market_trend = random.uniform(-20, 5)

        # Seasonal patterns (mock)
        seasonal_factor = "성수기" if random.random() > 0.5 else "비수기"

        return {
            "analysis": "Trend analysis completed",
            "period": trend_period,
            "trends": {
                "price_change": f"{price_trend:+.1f}%",
                "volume_change": f"{volume_trend:+.1f}%",
                "days_on_market_change": f"{days_on_market_trend:+.1f}%"
            },
            "patterns": {
                "seasonal": seasonal_factor,
                "momentum": "상승" if price_trend > 5 else "하락" if price_trend < -5 else "횡보",
                "volatility": "높음" if abs(price_trend) > 7 else "보통" if abs(price_trend) > 3 else "낮음"
            },
            "forecast": {
                "next_month": "상승 예상" if price_trend > 0 else "하락 예상",
                "confidence": f"{random.uniform(60, 85):.1f}%"
            }
        }


class ComparativeAnalyzer(BaseAnalysisTool):
    """Compares properties or regions"""

    def __init__(self):
        super().__init__(
            name="comparative_analyzer",
            description="Performs comparative analysis between different properties or regions"
        )

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform comparative analysis"""
        # Group data by region if available
        regions = {}
        for source, items in data.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        region = item.get("region", "Unknown")
                        if region not in regions:
                            regions[region] = []
                        regions[region].append(item)

        # Compare regions
        comparisons = {}
        for region, listings in regions.items():
            prices = []
            for listing in listings:
                if "price" in listing:
                    try:
                        price_str = listing["price"]
                        if isinstance(price_str, str):
                            price_num = float(price_str.replace("억", "").replace(",", "").strip())
                            prices.append(price_num)
                    except:
                        continue

            if prices:
                comparisons[region] = {
                    "average_price": f"{statistics.mean(prices):.1f}억",
                    "listing_count": len(listings),
                    "price_range": f"{min(prices):.1f}억 - {max(prices):.1f}억"
                }

        # Rank regions by average price
        if comparisons:
            ranked = sorted(comparisons.items(),
                          key=lambda x: float(x[1]["average_price"].replace("억", "")),
                          reverse=True)
            rankings = {region: idx + 1 for idx, (region, _) in enumerate(ranked)}
        else:
            ranked = []
            rankings = {}

        return {
            "analysis": "Comparative analysis completed",
            "comparisons": comparisons,
            "rankings": rankings,
            "insights": [
                f"총 {len(regions)}개 지역 비교 완료" if regions else "비교 가능한 데이터 없음",
                f"가장 높은 평균 가격: {ranked[0][0]}" if ranked else "",
                f"가장 낮은 평균 가격: {ranked[-1][0]}" if len(ranked) > 1 else ""
            ]
        }


class InvestmentEvaluator(BaseAnalysisTool):
    """Evaluates investment potential"""

    def __init__(self):
        super().__init__(
            name="investment_evaluator",
            description="Evaluates investment value and potential returns"
        )

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate investment potential"""
        # Mock investment metrics
        roi_estimate = random.uniform(3, 12)  # Annual ROI percentage
        payback_period = random.uniform(8, 15)  # Years
        rental_yield = random.uniform(2, 5)  # Percentage
        appreciation_potential = random.uniform(2, 8)  # Annual percentage

        # Investment score (0-100)
        investment_score = min(100, roi_estimate * 5 + appreciation_potential * 3 + rental_yield * 2)

        # Risk assessment
        risk_level = "높음" if investment_score < 40 else "중간" if investment_score < 70 else "낮음"

        return {
            "analysis": "Investment evaluation completed",
            "metrics": {
                "estimated_roi": f"{roi_estimate:.1f}%",
                "payback_period": f"{payback_period:.1f}년",
                "rental_yield": f"{rental_yield:.1f}%",
                "appreciation_potential": f"{appreciation_potential:.1f}%",
                "investment_score": round(investment_score)
            },
            "assessment": {
                "recommendation": "투자 적합" if investment_score > 60 else "신중 검토" if investment_score > 40 else "투자 부적합",
                "risk_level": risk_level,
                "best_holding_period": f"{random.randint(3, 7)}년",
                "liquidity": "높음" if random.random() > 0.5 else "보통"
            },
            "factors": {
                "positive": [
                    "안정적인 임대 수요" if rental_yield > 3 else None,
                    "높은 가격 상승 잠재력" if appreciation_potential > 5 else None,
                    "우수한 입지 조건" if random.random() > 0.5 else None
                ],
                "negative": [
                    "높은 초기 투자 비용" if random.random() > 0.5 else None,
                    "시장 변동성 존재" if risk_level == "높음" else None
                ]
            }
        }


class RiskAssessor(BaseAnalysisTool):
    """Assesses various risk factors"""

    def __init__(self):
        super().__init__(
            name="risk_assessor",
            description="Identifies and evaluates risk factors in real estate investments"
        )

    async def analyze(self, data: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assess risk factors"""
        # Mock risk assessment
        risk_scores = {
            "market_risk": random.uniform(20, 80),
            "liquidity_risk": random.uniform(20, 80),
            "regulatory_risk": random.uniform(10, 60),
            "economic_risk": random.uniform(30, 70),
            "location_risk": random.uniform(10, 50)
        }

        overall_risk = statistics.mean(risk_scores.values())

        # Identify major risks
        major_risks = []
        for risk_type, score in risk_scores.items():
            if score > 60:
                major_risks.append({
                    "type": risk_type.replace("_", " ").title(),
                    "level": "높음" if score > 70 else "중간",
                    "score": round(score)
                })

        # Mitigation strategies
        mitigation = []
        if risk_scores["market_risk"] > 60:
            mitigation.append("시장 동향 지속 모니터링 필요")
        if risk_scores["liquidity_risk"] > 60:
            mitigation.append("충분한 현금 유동성 확보 권장")
        if risk_scores["regulatory_risk"] > 50:
            mitigation.append("규제 변화 사전 대응 계획 수립")

        return {
            "analysis": "Risk assessment completed",
            "risk_scores": {k: round(v) for k, v in risk_scores.items()},
            "overall_risk": {
                "score": round(overall_risk),
                "level": "높음" if overall_risk > 60 else "중간" if overall_risk > 40 else "낮음"
            },
            "major_risks": major_risks,
            "mitigation_strategies": mitigation,
            "risk_factors": {
                "external": [
                    "금리 변동 가능성",
                    "부동산 규제 강화 가능성" if risk_scores["regulatory_risk"] > 40 else None,
                    "경기 침체 위험" if risk_scores["economic_risk"] > 50 else None
                ],
                "internal": [
                    "임대 공실 리스크" if random.random() > 0.5 else None,
                    "유지보수 비용 증가" if random.random() > 0.6 else None
                ]
            },
            "recommendation": "리스크 관리 전략 수립 필요" if overall_risk > 50 else "현재 리스크 수준 관리 가능"
        }


# Analysis tool registry
class AnalysisToolRegistry:
    """Registry for analysis tools"""

    _instance = None
    _tools = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_tools()
        return cls._instance

    def _initialize_tools(self):
        """Initialize all analysis tools"""
        self._tools = {
            "market_analyzer": MarketAnalyzer(),
            "trend_analyzer": TrendAnalyzer(),
            "comparative_analyzer": ComparativeAnalyzer(),
            "investment_evaluator": InvestmentEvaluator(),
            "risk_assessor": RiskAssessor()
        }
        logger.info(f"Initialized {len(self._tools)} analysis tools")

    def get(self, name: str) -> Optional[BaseAnalysisTool]:
        """Get analysis tool by name"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all available analysis tools"""
        return list(self._tools.keys())

    def get_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all tools"""
        return {name: tool.description for name, tool in self._tools.items()}


# Create singleton instance
analysis_tool_registry = AnalysisToolRegistry()
