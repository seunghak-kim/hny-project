"""
투자수익률(ROI) 계산 Tool
부동산 투자 수익률, 현금 흐름, 손익분기점 분석
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class ROICalculatorTool:
    """
    투자수익률 계산 도구
    매매/임대 수익률, 레버리지 효과, 현금흐름 분석
    """

    def __init__(self, loan_search_tool=None, tax_calculator=None):
        """
        초기화

        Args:
            loan_search_tool: 대출 상품 검색 도구 (선택적)
            tax_calculator: 세금 계산기 (선택적)
        """
        self.loan_search_tool = loan_search_tool
        self.tax_calculator = tax_calculator
        self.name = "roi_calculator"

        # 기본 설정값
        self.default_params = {
            "maintenance_rate": 0.002,  # 월 관리비율 (부동산 가격의 0.2%)
            "vacancy_rate": 0.05,       # 공실률 5%
            "price_growth_rate": 0.03,  # 연간 가격 상승률 3%
            "rent_growth_rate": 0.02,   # 연간 임대료 상승률 2%
            "inflation_rate": 0.025     # 물가상승률 2.5%
        }

        # 세율 정보
        self.tax_rates = {
            "acquisition_tax": 0.04,      # 취득세 (간소화)
            "property_tax": 0.002,         # 재산세 연 0.2%
            "income_tax": 0.154,          # 임대소득세 (간소화)
            "capital_gains_tax": 0.20     # 양도소득세 (간소화)
        }

        logger.info("ROICalculatorTool initialized")

    async def execute(
        self,
        property_price: float,
        down_payment: Optional[float] = None,
        monthly_rent: Optional[float] = None,
        loan_products: Optional[List[Dict]] = None,
        holding_period_years: int = 5,
        custom_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        ROI 계산 실행

        Args:
            property_price: 부동산 가격
            down_payment: 계약금/자기자본 (없으면 30% 가정)
            monthly_rent: 월 임대료 (임대 수익 계산시)
            loan_products: 대출 상품 정보 (없으면 자체 검색)
            holding_period_years: 보유 기간 (년)
            custom_params: 사용자 정의 파라미터

        Returns:
            ROI 분석 결과
        """
        try:
            logger.info(f"Calculating ROI for property price: {property_price:,}")

            # 파라미터 준비
            params = self._prepare_parameters(
                property_price, down_payment, custom_params
            )

            # 1. 대출 정보 확보
            if not loan_products and self.loan_search_tool:
                loan_products = await self._search_loan_products(
                    property_price - params["down_payment"]
                )

            best_loan = self._select_best_loan(loan_products) if loan_products else None

            # 2. 초기 투자 비용 계산
            initial_costs = self._calculate_initial_costs(property_price, params)

            # 3. 연간 현금 흐름 계산
            cash_flows = self._calculate_cash_flows(
                property_price, monthly_rent, best_loan,
                params, holding_period_years
            )

            # 4. 매각 시나리오 계산
            exit_scenarios = self._calculate_exit_scenarios(
                property_price, best_loan, params, holding_period_years
            )

            # 5. ROI 지표 계산
            roi_metrics = self._calculate_roi_metrics(
                initial_costs, cash_flows, exit_scenarios
            )

            # 6. 레버리지 효과 분석
            leverage_analysis = self._analyze_leverage_effect(
                property_price, params["down_payment"], roi_metrics
            )

            # 7. 민감도 분석
            sensitivity = self._sensitivity_analysis(
                property_price, monthly_rent, best_loan, params
            )

            # 8. 종합 평가
            evaluation = self._comprehensive_evaluation(
                roi_metrics, leverage_analysis, sensitivity
            )

            return {
                "status": "success",
                "property_price": property_price,
                "initial_investment": initial_costs,
                "loan_used": best_loan,
                "cash_flows": cash_flows,
                "exit_scenarios": exit_scenarios,
                "roi_metrics": roi_metrics,
                "leverage_analysis": leverage_analysis,
                "sensitivity_analysis": sensitivity,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"ROI calculation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "property_price": property_price,
                "timestamp": datetime.now().isoformat()
            }

    async def _search_loan_products(self, loan_amount: float) -> List[Dict]:
        """대출 상품 검색"""
        try:
            results = await self.loan_search_tool.search(
                loan_amount=loan_amount,
                loan_type="mortgage",
                sort_by="interest_rate"
            )
            return results.get("products", [])
        except Exception as e:
            logger.error(f"Loan search failed: {e}")
            return []

    def _prepare_parameters(
        self,
        property_price: float,
        down_payment: Optional[float],
        custom_params: Optional[Dict]
    ) -> Dict:
        """파라미터 준비"""
        params = self.default_params.copy()

        if custom_params:
            params.update(custom_params)

        # 계약금 설정
        if down_payment is None:
            params["down_payment"] = property_price * 0.3  # 기본 30%
        else:
            params["down_payment"] = down_payment

        params["loan_amount"] = property_price - params["down_payment"]

        return params

    def _select_best_loan(self, loan_products: List[Dict]) -> Dict:
        """최적 대출 상품 선택"""
        if not loan_products:
            # 기본값
            return {
                "product_name": "기본 주택담보대출",
                "interest_rate": 0.045,  # 4.5%
                "loan_term_years": 30,
                "monthly_payment": 0
            }

        # 금리가 가장 낮은 상품 선택
        best = min(loan_products, key=lambda x: x.get("interest_rate", 999))

        # 월 상환액 계산
        if not best.get("monthly_payment"):
            best["monthly_payment"] = self._calculate_monthly_payment(
                best.get("loan_amount", 0),
                best.get("interest_rate", 0.045),
                best.get("loan_term_years", 30)
            )

        return best

    def _calculate_initial_costs(
        self,
        property_price: float,
        params: Dict
    ) -> Dict[str, float]:
        """초기 투자 비용 계산"""
        costs = {
            "down_payment": params["down_payment"],
            "acquisition_tax": property_price * self.tax_rates["acquisition_tax"],
            "agent_fee": property_price * 0.005,  # 중개수수료 0.5%
            "registration_fee": property_price * 0.002,  # 등기비용 0.2%
            "other_costs": property_price * 0.001  # 기타 비용 0.1%
        }

        costs["total"] = sum(costs.values())

        return costs

    def _calculate_cash_flows(
        self,
        property_price: float,
        monthly_rent: Optional[float],
        loan: Optional[Dict],
        params: Dict,
        years: int
    ) -> List[Dict]:
        """연간 현금 흐름 계산"""
        cash_flows = []

        for year in range(1, years + 1):
            # 임대 수입
            if monthly_rent:
                # 임대료 상승 반영
                adjusted_rent = monthly_rent * ((1 + params["rent_growth_rate"]) ** (year - 1))
                annual_rent = adjusted_rent * 12 * (1 - params["vacancy_rate"])
            else:
                annual_rent = 0

            # 지출
            expenses = {
                "loan_payment": loan["monthly_payment"] * 12 if loan else 0,
                "property_tax": property_price * self.tax_rates["property_tax"],
                "maintenance": property_price * params["maintenance_rate"] * 12,
                "insurance": property_price * 0.001  # 보험료
            }

            if annual_rent > 0:
                # 임대소득세 (간소화 계산)
                taxable_income = annual_rent - sum(expenses.values())
                if taxable_income > 0:
                    expenses["income_tax"] = taxable_income * self.tax_rates["income_tax"]

            total_expenses = sum(expenses.values())
            net_cash_flow = annual_rent - total_expenses

            cash_flows.append({
                "year": year,
                "rental_income": round(annual_rent),
                "expenses": expenses,
                "total_expenses": round(total_expenses),
                "net_cash_flow": round(net_cash_flow),
                "cumulative_cash_flow": round(
                    sum(cf["net_cash_flow"] for cf in cash_flows) + net_cash_flow
                )
            })

        return cash_flows

    def _calculate_exit_scenarios(
        self,
        property_price: float,
        loan: Optional[Dict],
        params: Dict,
        years: int
    ) -> Dict[str, Any]:
        """매각 시나리오 계산"""
        scenarios = {}

        for scenario_name, growth_rate in [
            ("pessimistic", params["price_growth_rate"] - 0.02),
            ("base", params["price_growth_rate"]),
            ("optimistic", params["price_growth_rate"] + 0.02)
        ]:
            # 미래 가격
            future_price = property_price * ((1 + growth_rate) ** years)

            # 남은 대출 잔액
            if loan:
                remaining_loan = self._calculate_remaining_loan(
                    loan.get("loan_amount", params["loan_amount"]),
                    loan.get("interest_rate", 0.045),
                    loan.get("loan_term_years", 30),
                    years
                )
            else:
                remaining_loan = 0

            # 양도소득세 (간소화)
            capital_gain = future_price - property_price
            if capital_gain > 0:
                capital_gains_tax = capital_gain * self.tax_rates["capital_gains_tax"]
            else:
                capital_gains_tax = 0

            # 순 수익
            net_proceeds = future_price - remaining_loan - capital_gains_tax

            scenarios[scenario_name] = {
                "future_price": round(future_price),
                "price_appreciation": round(future_price - property_price),
                "remaining_loan": round(remaining_loan),
                "capital_gains_tax": round(capital_gains_tax),
                "net_proceeds": round(net_proceeds),
                "total_return": round(net_proceeds - params["down_payment"])
            }

        return scenarios

    def _calculate_roi_metrics(
        self,
        initial_costs: Dict,
        cash_flows: List[Dict],
        exit_scenarios: Dict
    ) -> Dict[str, Any]:
        """ROI 지표 계산"""
        # 기본 시나리오 사용
        base_scenario = exit_scenarios["base"]

        # 총 현금 흐름
        total_cash_flow = sum(cf["net_cash_flow"] for cf in cash_flows)

        # 총 수익 (현금흐름 + 매각수익)
        total_return = total_cash_flow + base_scenario["total_return"]

        # ROI 계산
        roi = (total_return / initial_costs["total"]) * 100

        # 연평균 수익률
        years = len(cash_flows)
        annual_return = ((1 + total_return / initial_costs["total"]) ** (1/years) - 1) * 100

        # Cash-on-Cash Return (현금수익률)
        if cash_flows and cash_flows[0]["net_cash_flow"] != 0:
            cash_on_cash = (cash_flows[0]["net_cash_flow"] / initial_costs["down_payment"]) * 100
        else:
            cash_on_cash = 0

        # 손익분기점
        breakeven_year = None
        for i, cf in enumerate(cash_flows):
            if cf["cumulative_cash_flow"] > 0:
                breakeven_year = i + 1
                break

        return {
            "total_return": round(total_return),
            "roi_percentage": round(roi, 2),
            "annual_return": round(annual_return, 2),
            "cash_on_cash_return": round(cash_on_cash, 2),
            "breakeven_year": breakeven_year,
            "total_cash_flow": round(total_cash_flow)
        }

    def _analyze_leverage_effect(
        self,
        property_price: float,
        down_payment: float,
        roi_metrics: Dict
    ) -> Dict[str, Any]:
        """레버리지 효과 분석"""
        ltv_ratio = ((property_price - down_payment) / property_price) * 100

        # 레버리지 배수
        leverage_multiple = property_price / down_payment

        # 레버리지 효과
        if roi_metrics["roi_percentage"] > 0:
            leverage_effect = "positive"
            effect_description = "대출을 활용한 투자가 유리합니다."
        else:
            leverage_effect = "negative"
            effect_description = "대출 비용이 수익을 초과합니다."

        return {
            "ltv_ratio": round(ltv_ratio, 1),
            "leverage_multiple": round(leverage_multiple, 1),
            "leverage_effect": leverage_effect,
            "description": effect_description,
            "risk_level": self._assess_leverage_risk(ltv_ratio)
        }

    def _sensitivity_analysis(
        self,
        property_price: float,
        monthly_rent: Optional[float],
        loan: Optional[Dict],
        params: Dict
    ) -> Dict[str, Any]:
        """민감도 분석"""
        sensitivity = {}

        # 임대료 변화 민감도
        if monthly_rent:
            rent_scenarios = {}
            for change_pct in [-10, -5, 0, 5, 10]:
                adjusted_rent = monthly_rent * (1 + change_pct/100)
                annual_income = adjusted_rent * 12 * (1 - params["vacancy_rate"])
                annual_expenses = (loan["monthly_payment"] * 12 if loan else 0) + \
                                property_price * (self.tax_rates["property_tax"] + params["maintenance_rate"] * 12)
                net_income = annual_income - annual_expenses
                rent_scenarios[f"{change_pct:+d}%"] = round(net_income)

            sensitivity["rent_change"] = rent_scenarios

        # 금리 변화 민감도
        if loan:
            rate_scenarios = {}
            base_rate = loan.get("interest_rate", 0.045)
            for change_pct in [-1, -0.5, 0, 0.5, 1]:
                new_rate = base_rate + change_pct/100
                new_payment = self._calculate_monthly_payment(
                    loan.get("loan_amount", params["loan_amount"]),
                    new_rate,
                    loan.get("loan_term_years", 30)
                )
                annual_payment = new_payment * 12
                rate_scenarios[f"{change_pct:+.1f}%p"] = round(annual_payment)

            sensitivity["interest_rate_change"] = rate_scenarios

        # 부동산 가격 변화 민감도
        price_scenarios = {}
        for change_pct in [-10, -5, 0, 5, 10]:
            future_price = property_price * (1 + change_pct/100)
            price_scenarios[f"{change_pct:+d}%"] = round(future_price)

        sensitivity["price_change"] = price_scenarios

        return sensitivity

    def _comprehensive_evaluation(
        self,
        roi_metrics: Dict,
        leverage_analysis: Dict,
        sensitivity: Dict
    ) -> Dict[str, Any]:
        """종합 평가"""
        # 점수 계산
        score = 50

        # ROI 기준
        if roi_metrics["roi_percentage"] > 20:
            score += 20
        elif roi_metrics["roi_percentage"] > 10:
            score += 10
        elif roi_metrics["roi_percentage"] < 0:
            score -= 20

        # 연평균 수익률 기준
        if roi_metrics["annual_return"] > 7:
            score += 15
        elif roi_metrics["annual_return"] > 4:
            score += 5
        elif roi_metrics["annual_return"] < 0:
            score -= 15

        # 현금흐름 기준
        if roi_metrics["cash_on_cash_return"] > 5:
            score += 10
        elif roi_metrics["cash_on_cash_return"] > 0:
            score += 5
        elif roi_metrics["cash_on_cash_return"] < -5:
            score -= 10

        # 레버리지 리스크
        if leverage_analysis["risk_level"] == "high":
            score -= 10
        elif leverage_analysis["risk_level"] == "low":
            score += 5

        # 등급 결정
        if score >= 80:
            grade = "excellent"
            recommendation = "매우 우수한 투자입니다."
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

        # 주요 강점과 약점
        strengths = []
        weaknesses = []

        if roi_metrics["roi_percentage"] > 15:
            strengths.append(f"높은 ROI ({roi_metrics['roi_percentage']}%)")
        elif roi_metrics["roi_percentage"] < 5:
            weaknesses.append(f"낮은 ROI ({roi_metrics['roi_percentage']}%)")

        if roi_metrics["cash_on_cash_return"] > 5:
            strengths.append(f"우수한 현금수익률 ({roi_metrics['cash_on_cash_return']}%)")
        elif roi_metrics["cash_on_cash_return"] < 0:
            weaknesses.append("음의 현금흐름")

        if leverage_analysis["leverage_effect"] == "positive":
            strengths.append("긍정적 레버리지 효과")
        else:
            weaknesses.append("부정적 레버리지 효과")

        return {
            "score": round(score),
            "grade": grade,
            "recommendation": recommendation,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "key_metrics_summary": {
                "roi": f"{roi_metrics['roi_percentage']}%",
                "annual_return": f"{roi_metrics['annual_return']}%",
                "cash_on_cash": f"{roi_metrics['cash_on_cash_return']}%",
                "breakeven": f"{roi_metrics['breakeven_year']}년" if roi_metrics['breakeven_year'] else "없음"
            }
        }

    def _calculate_monthly_payment(
        self,
        loan_amount: float,
        annual_rate: float,
        years: int
    ) -> float:
        """월 상환액 계산"""
        if annual_rate == 0:
            return loan_amount / (years * 12)

        monthly_rate = annual_rate / 12
        months = years * 12

        payment = loan_amount * (monthly_rate * (1 + monthly_rate)**months) / \
                 ((1 + monthly_rate)**months - 1)

        return payment

    def _calculate_remaining_loan(
        self,
        loan_amount: float,
        annual_rate: float,
        total_years: int,
        elapsed_years: int
    ) -> float:
        """남은 대출 잔액 계산"""
        if annual_rate == 0:
            return loan_amount * (1 - elapsed_years/total_years)

        monthly_rate = annual_rate / 12
        total_months = total_years * 12
        elapsed_months = elapsed_years * 12

        # 원리금 균등상환 방식 가정
        monthly_payment = self._calculate_monthly_payment(loan_amount, annual_rate, total_years)

        # 남은 잔액 계산
        remaining = loan_amount * ((1 + monthly_rate)**elapsed_months) - \
                   monthly_payment * (((1 + monthly_rate)**elapsed_months - 1) / monthly_rate)

        return max(0, remaining)

    def _assess_leverage_risk(self, ltv_ratio: float) -> str:
        """레버리지 리스크 평가"""
        if ltv_ratio > 80:
            return "high"
        elif ltv_ratio > 60:
            return "medium"
        else:
            return "low"


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_roi_calculator():
        calculator = ROICalculatorTool()

        # 테스트 케이스
        result = await calculator.execute(
            property_price=1000000000,  # 10억
            down_payment=300000000,      # 3억 (30%)
            monthly_rent=3000000,         # 월세 300만원
            holding_period_years=5
        )

        print("=== ROI Calculation Result ===")
        print(f"Status: {result['status']}")

        print(f"\n초기 투자:")
        for key, value in result['initial_investment'].items():
            if key != 'total':
                print(f"  {key}: {value:,.0f}원")
        print(f"  총계: {result['initial_investment']['total']:,.0f}원")

        print(f"\nROI 지표:")
        metrics = result['roi_metrics']
        print(f"  총 수익: {metrics['total_return']:,}원")
        print(f"  ROI: {metrics['roi_percentage']}%")
        print(f"  연평균 수익률: {metrics['annual_return']}%")
        print(f"  현금수익률: {metrics['cash_on_cash_return']}%")
        print(f"  손익분기점: {metrics['breakeven_year']}년" if metrics['breakeven_year'] else "  손익분기점: 없음")

        print(f"\n종합 평가:")
        eval = result['evaluation']
        print(f"  점수: {eval['score']}/100")
        print(f"  등급: {eval['grade']}")
        print(f"  추천: {eval['recommendation']}")

    asyncio.run(test_roi_calculator())