"""
대출 한도 및 금리 시뮬레이션 Tool
사용자 조건에 따른 대출 가능 금액, 금리, 상환 계획 시뮬레이션
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class LoanSimulatorTool:
    """
    대출 시뮬레이션 도구
    DTI, LTV, DSR 기반 대출 한도 계산 및 상환 시뮬레이션
    """

    def __init__(self, loan_search_tool=None):
        """
        초기화

        Args:
            loan_search_tool: 대출 상품 검색 도구 (선택적)
        """
        self.loan_search_tool = loan_search_tool
        self.name = "loan_simulator"

        # 규제 기준 (2024년 기준)
        self.regulation_limits = {
            "ltv": {  # Loan to Value (주택담보대출비율)
                "서울": {"규제지역": 0.4, "비규제": 0.5},
                "수도권": {"규제지역": 0.5, "비규제": 0.6},
                "지방": {"규제지역": 0.6, "비규제": 0.7}
            },
            "dti": 0.4,  # Debt to Income (총부채상환비율) 40%
            "dsr": 0.4   # Debt Service Ratio (총부채원리금상환비율) 40%
        }

        # 금리 테이블 (신용등급별)
        self.interest_rates = {
            1: {"min": 3.5, "max": 4.5},  # 1등급
            2: {"min": 4.0, "max": 5.0},  # 2등급
            3: {"min": 4.5, "max": 5.5},  # 3등급
            4: {"min": 5.0, "max": 6.5},  # 4등급
            5: {"min": 5.5, "max": 7.5},  # 5등급
            6: {"min": 6.5, "max": 9.0},  # 6등급
            7: {"min": 8.0, "max": 12.0}  # 7등급 이하
        }

        # 대출 상품 유형
        self.loan_types = {
            "주택담보대출": {"ltv_bonus": 0, "rate_discount": 0},
            "전세자금대출": {"ltv_bonus": 0.1, "rate_discount": 0.5},
            "신혼부부대출": {"ltv_bonus": 0.1, "rate_discount": 1.0},
            "청년대출": {"ltv_bonus": 0.05, "rate_discount": 0.8},
            "디딤돌대출": {"ltv_bonus": 0.1, "rate_discount": 1.2}
        }

        logger.info("LoanSimulatorTool initialized")

    async def execute(
        self,
        property_price: float,
        annual_income: float,
        existing_loans: Optional[List[Dict]] = None,
        credit_score: int = 3,
        region: str = "서울",
        is_regulated: bool = True,
        loan_type: str = "주택담보대출",
        preferred_term_years: int = 30,
        available_down_payment: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        대출 시뮬레이션 실행

        Args:
            property_price: 부동산 가격
            annual_income: 연소득
            existing_loans: 기존 대출 정보
            credit_score: 신용등급 (1-7)
            region: 지역 (서울/수도권/지방)
            is_regulated: 규제지역 여부
            loan_type: 대출 상품 유형
            preferred_term_years: 희망 대출 기간
            available_down_payment: 가용 자기자본

        Returns:
            시뮬레이션 결과
        """
        try:
            logger.info(f"Simulating loan for property: {property_price:,}, income: {annual_income:,}")

            # 1. 대출 한도 계산
            max_loan = self._calculate_max_loan(
                property_price, annual_income, existing_loans,
                region, is_regulated, loan_type
            )

            # 2. 금리 산정
            interest_rate = self._calculate_interest_rate(
                credit_score, loan_type, max_loan["loan_amount"]
            )

            # 3. 상환 계획 수립
            repayment_plan = self._create_repayment_plan(
                max_loan["loan_amount"], interest_rate,
                preferred_term_years, annual_income
            )

            # 4. 대출 상품 검색 (가능한 경우)
            loan_products = None
            if self.loan_search_tool:
                loan_products = await self._search_suitable_loans(
                    max_loan["loan_amount"], credit_score, loan_type
                )

            # 5. 자기자본 요구사항 계산
            capital_requirement = self._calculate_capital_requirement(
                property_price, max_loan["loan_amount"], available_down_payment
            )

            # 6. 대출 가능성 평가
            feasibility = self._assess_loan_feasibility(
                max_loan, repayment_plan, capital_requirement
            )

            # 7. 대안 시나리오
            alternatives = self._generate_alternatives(
                property_price, annual_income, max_loan, interest_rate
            )

            # 8. 주의사항 및 팁
            tips = self._generate_tips(
                credit_score, max_loan, repayment_plan, feasibility
            )

            return {
                "status": "success",
                "property_price": property_price,
                "annual_income": annual_income,
                "max_loan": max_loan,
                "interest_rate": interest_rate,
                "repayment_plan": repayment_plan,
                "loan_products": loan_products,
                "capital_requirement": capital_requirement,
                "feasibility": feasibility,
                "alternatives": alternatives,
                "tips": tips,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Loan simulation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "property_price": property_price,
                "timestamp": datetime.now().isoformat()
            }

    def _calculate_max_loan(
        self,
        property_price: float,
        annual_income: float,
        existing_loans: Optional[List[Dict]],
        region: str,
        is_regulated: bool,
        loan_type: str
    ) -> Dict[str, Any]:
        """최대 대출 한도 계산"""
        # LTV 한도
        regulation_type = "규제지역" if is_regulated else "비규제"
        base_ltv = self.regulation_limits["ltv"].get(region, {}).get(regulation_type, 0.5)

        # 대출 상품별 LTV 보너스
        ltv_bonus = self.loan_types.get(loan_type, {}).get("ltv_bonus", 0)
        max_ltv = min(base_ltv + ltv_bonus, 0.9)  # 최대 90%

        ltv_limit = property_price * max_ltv

        # DTI 한도
        monthly_income = annual_income / 12
        max_monthly_payment_dti = monthly_income * self.regulation_limits["dti"]

        # 기존 대출 상환액 차감
        existing_monthly_payment = 0
        if existing_loans:
            for loan in existing_loans:
                existing_monthly_payment += loan.get("monthly_payment", 0)

        available_monthly_payment = max_monthly_payment_dti - existing_monthly_payment

        # DTI 기준 최대 대출 (30년, 연 5% 가정)
        dti_limit = self._calculate_loan_from_payment(
            available_monthly_payment, 0.05, 30
        )

        # DSR 한도 (원리금 상환 기준)
        max_monthly_payment_dsr = monthly_income * self.regulation_limits["dsr"]
        available_monthly_payment_dsr = max_monthly_payment_dsr - existing_monthly_payment

        dsr_limit = self._calculate_loan_from_payment(
            available_monthly_payment_dsr, 0.05, 30
        )

        # 최종 한도 (가장 작은 값)
        final_limit = min(ltv_limit, dti_limit, dsr_limit)

        return {
            "loan_amount": round(final_limit),
            "ltv_limit": round(ltv_limit),
            "dti_limit": round(dti_limit),
            "dsr_limit": round(dsr_limit),
            "limiting_factor": self._get_limiting_factor(final_limit, ltv_limit, dti_limit, dsr_limit),
            "ltv_ratio": round((final_limit / property_price) * 100, 1),
            "details": {
                "max_ltv": f"{max_ltv*100:.0f}%",
                "monthly_income": round(monthly_income),
                "existing_payments": round(existing_monthly_payment),
                "available_payment": round(available_monthly_payment)
            }
        }

    def _calculate_interest_rate(
        self,
        credit_score: int,
        loan_type: str,
        loan_amount: float
    ) -> Dict[str, Any]:
        """금리 산정"""
        # 기본 금리 (신용등급별)
        rate_range = self.interest_rates.get(credit_score, self.interest_rates[4])
        base_rate = (rate_range["min"] + rate_range["max"]) / 2

        # 대출 상품별 금리 할인
        rate_discount = self.loan_types.get(loan_type, {}).get("rate_discount", 0)

        # 대출 금액별 조정 (고액 대출은 금리 상승)
        if loan_amount > 1000000000:  # 10억 초과
            amount_adjustment = 0.3
        elif loan_amount > 500000000:  # 5억 초과
            amount_adjustment = 0.2
        else:
            amount_adjustment = 0

        final_rate = base_rate - rate_discount + amount_adjustment
        final_rate = max(rate_range["min"], min(final_rate, rate_range["max"]))

        return {
            "annual_rate": round(final_rate, 2),
            "monthly_rate": round(final_rate / 12, 4),
            "credit_score": credit_score,
            "base_rate": round(base_rate, 2),
            "discount_applied": round(rate_discount, 2),
            "final_rate_range": {
                "min": round(max(rate_range["min"] - rate_discount, 2.5), 2),
                "max": round(rate_range["max"], 2)
            }
        }

    def _create_repayment_plan(
        self,
        loan_amount: float,
        interest_rate: Dict,
        term_years: int,
        annual_income: float
    ) -> Dict[str, Any]:
        """상환 계획 수립"""
        annual_rate = interest_rate["annual_rate"] / 100
        monthly_rate = annual_rate / 12
        total_months = term_years * 12

        # 원리금균등상환 계산
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**total_months) / \
                            ((1 + monthly_rate)**total_months - 1)
        else:
            monthly_payment = loan_amount / total_months

        # 총 상환액
        total_payment = monthly_payment * total_months
        total_interest = total_payment - loan_amount

        # 소득 대비 상환 부담
        monthly_income = annual_income / 12
        payment_burden = (monthly_payment / monthly_income) * 100

        # 연도별 상환 계획 (처음 5년)
        yearly_breakdown = []
        remaining_balance = loan_amount

        for year in range(1, min(6, term_years + 1)):
            year_principal = 0
            year_interest = 0

            for month in range(12):
                if remaining_balance <= 0:
                    break

                # 이자 계산
                month_interest = remaining_balance * monthly_rate
                month_principal = monthly_payment - month_interest

                year_interest += month_interest
                year_principal += month_principal
                remaining_balance -= month_principal

            yearly_breakdown.append({
                "year": year,
                "principal": round(year_principal),
                "interest": round(year_interest),
                "total_payment": round(year_principal + year_interest),
                "remaining_balance": round(max(0, remaining_balance))
            })

        return {
            "loan_amount": round(loan_amount),
            "term_years": term_years,
            "monthly_payment": round(monthly_payment),
            "total_payment": round(total_payment),
            "total_interest": round(total_interest),
            "payment_burden_pct": round(payment_burden, 1),
            "yearly_breakdown": yearly_breakdown,
            "affordability": self._assess_affordability(payment_burden)
        }

    async def _search_suitable_loans(
        self,
        loan_amount: float,
        credit_score: int,
        loan_type: str
    ) -> List[Dict]:
        """적합한 대출 상품 검색"""
        try:
            if not self.loan_search_tool:
                return []

            results = await self.loan_search_tool.search(
                loan_amount=loan_amount,
                credit_score=credit_score,
                loan_type=loan_type,
                limit=5
            )

            products = []
            for product in results.get("products", [])[:5]:
                products.append({
                    "name": product.get("name"),
                    "bank": product.get("bank"),
                    "interest_rate": product.get("interest_rate"),
                    "max_amount": product.get("max_amount"),
                    "requirements": product.get("requirements", []),
                    "benefits": product.get("benefits", [])
                })

            return products

        except Exception as e:
            logger.error(f"Loan product search failed: {e}")
            return []

    def _calculate_capital_requirement(
        self,
        property_price: float,
        max_loan: float,
        available_capital: Optional[float]
    ) -> Dict[str, Any]:
        """자기자본 요구사항 계산"""
        # 필요 자기자본
        required_down_payment = property_price - max_loan

        # 부대비용 (취득세, 중개수수료 등)
        additional_costs = {
            "acquisition_tax": property_price * 0.04,  # 취득세 약 4%
            "agent_fee": property_price * 0.005,       # 중개수수료 0.5%
            "registration_fee": property_price * 0.002, # 등기비용 0.2%
            "other_costs": property_price * 0.003      # 기타 0.3%
        }

        total_additional = sum(additional_costs.values())
        total_required = required_down_payment + total_additional

        # 자금 충족 여부
        if available_capital is not None:
            shortage = max(0, total_required - available_capital)
            is_sufficient = shortage == 0
        else:
            shortage = None
            is_sufficient = None

        return {
            "required_down_payment": round(required_down_payment),
            "additional_costs": {k: round(v) for k, v in additional_costs.items()},
            "total_additional_costs": round(total_additional),
            "total_required": round(total_required),
            "available_capital": round(available_capital) if available_capital else None,
            "shortage": round(shortage) if shortage is not None else None,
            "is_sufficient": is_sufficient,
            "down_payment_ratio": round((required_down_payment / property_price) * 100, 1)
        }

    def _assess_loan_feasibility(
        self,
        max_loan: Dict,
        repayment_plan: Dict,
        capital_requirement: Dict
    ) -> Dict[str, Any]:
        """대출 가능성 평가"""
        score = 0
        factors = []
        risks = []

        # 상환 부담 평가
        burden = repayment_plan["payment_burden_pct"]
        if burden < 20:
            score += 30
            factors.append("낮은 상환 부담")
        elif burden < 30:
            score += 20
            factors.append("적정 상환 부담")
        elif burden < 40:
            score += 10
            factors.append("관리 가능한 상환 부담")
        else:
            risks.append("높은 상환 부담")

        # LTV 평가
        ltv = max_loan["ltv_ratio"]
        if ltv < 40:
            score += 20
            factors.append("낮은 LTV")
        elif ltv < 60:
            score += 15
            factors.append("적정 LTV")
        else:
            score += 5
            risks.append("높은 LTV로 인한 리스크")

        # 자기자본 충족도
        if capital_requirement["is_sufficient"]:
            score += 30
            factors.append("충분한 자기자본")
        elif capital_requirement["is_sufficient"] is False:
            risks.append(f"자기자본 부족 ({capital_requirement['shortage']:,}원)")

        # 한도 제약 요인
        limiting = max_loan["limiting_factor"]
        if limiting == "ltv":
            factors.append("LTV 기준 충족")
            score += 10
        elif limiting == "dti":
            risks.append("DTI 한도 제약")
        elif limiting == "dsr":
            risks.append("DSR 한도 제약")

        # 종합 평가
        if score >= 70:
            feasibility = "high"
            recommendation = "대출 승인 가능성이 높습니다."
        elif score >= 50:
            feasibility = "medium"
            recommendation = "대출 승인 가능하나 조건 개선이 필요할 수 있습니다."
        else:
            feasibility = "low"
            recommendation = "대출 승인이 어려울 수 있으니 대안을 검토하세요."

        return {
            "feasibility_score": score,
            "feasibility_level": feasibility,
            "positive_factors": factors,
            "risk_factors": risks,
            "recommendation": recommendation
        }

    def _generate_alternatives(
        self,
        property_price: float,
        annual_income: float,
        max_loan: Dict,
        interest_rate: Dict
    ) -> List[Dict]:
        """대안 시나리오 생성"""
        alternatives = []

        # 1. 낮은 가격대 물건
        lower_price = property_price * 0.8
        lower_loan = min(lower_price * 0.7, max_loan["dti_limit"])
        alternatives.append({
            "scenario": "20% 저렴한 물건",
            "property_price": round(lower_price),
            "loan_amount": round(lower_loan),
            "down_payment": round(lower_price - lower_loan),
            "monthly_payment": round(self._calculate_monthly_payment(
                lower_loan, interest_rate["annual_rate"]/100, 30
            ))
        })

        # 2. 자기자본 증대
        increased_down = property_price * 0.4
        reduced_loan = property_price - increased_down
        alternatives.append({
            "scenario": "자기자본 40%로 증대",
            "property_price": round(property_price),
            "loan_amount": round(reduced_loan),
            "down_payment": round(increased_down),
            "monthly_payment": round(self._calculate_monthly_payment(
                reduced_loan, interest_rate["annual_rate"]/100, 30
            ))
        })

        # 3. 소득 증대 (20%)
        increased_income = annual_income * 1.2
        increased_dti = (increased_income / 12) * self.regulation_limits["dti"] * 12
        new_loan = min(increased_dti, property_price * 0.7)
        alternatives.append({
            "scenario": "소득 20% 증가시",
            "required_income": round(increased_income),
            "loan_amount": round(new_loan),
            "down_payment": round(property_price - new_loan),
            "monthly_payment": round(self._calculate_monthly_payment(
                new_loan, interest_rate["annual_rate"]/100, 30
            ))
        })

        return alternatives

    def _generate_tips(
        self,
        credit_score: int,
        max_loan: Dict,
        repayment_plan: Dict,
        feasibility: Dict
    ) -> List[str]:
        """대출 팁 생성"""
        tips = []

        # 신용등급 관련
        if credit_score > 3:
            tips.append(f"신용등급 개선시 금리를 {(credit_score-3)*0.5}%p 낮출 수 있습니다.")

        # 한도 관련
        if max_loan["limiting_factor"] == "dti":
            tips.append("소득 증빙을 보완하거나 기존 대출을 정리하면 한도가 증가합니다.")
        elif max_loan["limiting_factor"] == "dsr":
            tips.append("대출 기간을 늘리거나 기존 부채를 줄이면 한도가 증가합니다.")

        # 상환 부담 관련
        if repayment_plan["payment_burden_pct"] > 35:
            tips.append("상환 부담이 높습니다. 대출 기간 연장을 고려하세요.")

        # 금리 관련
        tips.append("주택금융공사 보금자리론, 디딤돌대출 등 정책 대출을 확인하세요.")

        # 자기자본 관련
        if feasibility.get("feasibility_level") == "low":
            tips.append("자기자본을 늘리거나 저렴한 물건을 찾는 것이 유리합니다.")

        # 일반 팁
        tips.append("여러 은행의 대출 조건을 비교하고 우대금리 조건을 확인하세요.")

        return tips[:5]  # 최대 5개

    def _calculate_loan_from_payment(
        self,
        monthly_payment: float,
        annual_rate: float,
        years: int
    ) -> float:
        """월 상환액으로부터 대출 가능액 역산"""
        if annual_rate == 0:
            return monthly_payment * years * 12

        monthly_rate = annual_rate / 12
        months = years * 12

        loan_amount = monthly_payment * ((1 + monthly_rate)**months - 1) / \
                     (monthly_rate * (1 + monthly_rate)**months)

        return loan_amount

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

    def _get_limiting_factor(
        self,
        final: float,
        ltv: float,
        dti: float,
        dsr: float
    ) -> str:
        """제한 요인 판별"""
        if final == ltv:
            return "ltv"
        elif final == dti:
            return "dti"
        elif final == dsr:
            return "dsr"
        else:
            return "unknown"

    def _assess_affordability(self, burden_pct: float) -> str:
        """상환 부담 평가"""
        if burden_pct < 20:
            return "very_comfortable"
        elif burden_pct < 30:
            return "comfortable"
        elif burden_pct < 40:
            return "manageable"
        elif burden_pct < 50:
            return "burdensome"
        else:
            return "very_burdensome"


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_loan_simulator():
        simulator = LoanSimulatorTool()

        # 테스트 케이스
        result = await simulator.execute(
            property_price=800000000,  # 8억
            annual_income=100000000,   # 연소득 1억
            existing_loans=[
                {"name": "신용대출", "monthly_payment": 500000}
            ],
            credit_score=2,
            region="서울",
            is_regulated=True,
            loan_type="주택담보대출",
            preferred_term_years=30,
            available_down_payment=300000000  # 3억
        )

        print("=== Loan Simulation Result ===")
        print(f"Status: {result['status']}")

        print(f"\n최대 대출 한도:")
        max_loan = result['max_loan']
        print(f"  대출 가능액: {max_loan['loan_amount']:,}원")
        print(f"  LTV 한도: {max_loan['ltv_limit']:,}원")
        print(f"  DTI 한도: {max_loan['dti_limit']:,}원")
        print(f"  DSR 한도: {max_loan['dsr_limit']:,}원")
        print(f"  제한 요인: {max_loan['limiting_factor'].upper()}")

        print(f"\n금리 정보:")
        rate = result['interest_rate']
        print(f"  연 금리: {rate['annual_rate']}%")
        print(f"  신용등급: {rate['credit_score']}등급")

        print(f"\n상환 계획:")
        repayment = result['repayment_plan']
        print(f"  월 상환액: {repayment['monthly_payment']:,}원")
        print(f"  총 이자: {repayment['total_interest']:,}원")
        print(f"  소득 대비 상환 부담: {repayment['payment_burden_pct']}%")

        print(f"\n대출 가능성:")
        feasibility = result['feasibility']
        print(f"  평가: {feasibility['feasibility_level'].upper()}")
        print(f"  점수: {feasibility['feasibility_score']}/100")
        print(f"  추천: {feasibility['recommendation']}")

    asyncio.run(test_loan_simulator())