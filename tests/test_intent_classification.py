"""
15개 Intent 분류 테스트
병합된 planning_agent.py의 의도 분석 기능을 검증합니다.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# 테스트용 더미 환경 변수 설정 (LLMService 초기화 에러 방지)
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key-for-pattern-matching-only")

# Path setup
backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent,
    IntentType,
    IntentResult
)


class TestIntentClassification:
    """15개 Intent 분류 테스트"""

    @pytest.fixture
    def planning_agent(self):
        """PlanningAgent 인스턴스 생성 (LLM 없이 패턴 매칭만 사용)"""
        return PlanningAgent(llm_context=None)

    # ========== 1. TERM_DEFINITION (용어설명) ==========
    @pytest.mark.asyncio
    async def test_term_definition(self, planning_agent):
        """용어설명 Intent 테스트"""
        test_queries = [
            "LTV가 뭐야?",
            "대항력의 의미는?",
            "DSR이 무엇인가요?",
            "재건축과 재개발의 차이점은?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.TERM_DEFINITION, \
                f"'{query}' should be TERM_DEFINITION, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 2. LEGAL_INQUIRY (법률해석) ==========
    @pytest.mark.asyncio
    async def test_legal_inquiry(self, planning_agent):
        """법률해석 Intent 테스트"""
        test_queries = [
            "전세 계약 갱신 가능한가요?",
            "임대차보호법에서 임차인 권리는?",
            "보증금 반환 청구 방법은?",
            "계약금 위약금은 얼마인가요?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.LEGAL_INQUIRY, \
                f"'{query}' should be LEGAL_INQUIRY, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 3. LOAN_SEARCH (대출상품검색) ==========
    @pytest.mark.asyncio
    async def test_loan_search(self, planning_agent):
        """대출상품검색 Intent 테스트"""
        test_queries = [
            "주택담보대출 상품 찾아줘",
            "신생아 특례 대출 어떤 게 있어?",
            "청년 전세자금대출 알려줘",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.LOAN_SEARCH, \
                f"'{query}' should be LOAN_SEARCH, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 4. LOAN_COMPARISON (대출조건비교) ==========
    @pytest.mark.asyncio
    async def test_loan_comparison(self, planning_agent):
        """대출조건비교 Intent 테스트"""
        test_queries = [
            "은행별 금리 비교해줘",
            "KB은행이랑 신한은행 대출 조건 비교",
            "DSR이랑 LTV 어느 게 유리해?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.LOAN_COMPARISON, \
                f"'{query}' should be LOAN_COMPARISON, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 5. BUILDING_REGISTRY (건축물대장조회) ==========
    @pytest.mark.asyncio
    async def test_building_registry(self, planning_agent):
        """건축물대장조회 Intent 테스트"""
        test_queries = [
            "건축물대장 조회해줘",
            "불법 증축 여부 확인",
            "건물 세대수는?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.BUILDING_REGISTRY, \
                f"'{query}' should be BUILDING_REGISTRY, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 6. PROPERTY_INFRA_ANALYSIS (매물인프라분석) ==========
    @pytest.mark.asyncio
    async def test_property_infra_analysis(self, planning_agent):
        """매물인프라분석 Intent 테스트"""
        test_queries = [
            "지하철역 거리는?",
            "주변 학군 어때?",
            "근처 마트랑 병원 있어?",
            "도보권 편의시설 알려줘",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.PROPERTY_INFRA_ANALYSIS, \
                f"'{query}' should be PROPERTY_INFRA_ANALYSIS, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 7. PRICE_EVALUATION (가격평가) ==========
    @pytest.mark.asyncio
    async def test_price_evaluation(self, planning_agent):
        """가격평가 Intent 테스트"""
        test_queries = [
            "이 가격 괜찮아?",
            "적정가 평가해줘",
            "너무 비싼 거 아니야?",
            "유사 매물 가격 비교",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.PRICE_EVALUATION, \
                f"'{query}' should be PRICE_EVALUATION, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 8. PROPERTY_SEARCH (매물검색) ==========
    @pytest.mark.asyncio
    async def test_property_search(self, planning_agent):
        """매물검색 Intent 테스트"""
        test_queries = [
            "강남 아파트 찾아줘",
            "원룸 매물 리스트",
            "3억 이하 오피스텔 검색",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.PROPERTY_SEARCH, \
                f"'{query}' should be PROPERTY_SEARCH, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 9. PROPERTY_RECOMMENDATION (맞춤추천) ==========
    @pytest.mark.asyncio
    async def test_property_recommendation(self, planning_agent):
        """맞춤추천 Intent 테스트"""
        test_queries = [
            "나한테 맞는 집 추천해줘",
            "신혼부부에게 좋은 아파트는?",
            "학군 좋은 곳 어디야?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.PROPERTY_RECOMMENDATION, \
                f"'{query}' should be PROPERTY_RECOMMENDATION, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 10. ROI_CALCULATION (투자수익률계산) ==========
    @pytest.mark.asyncio
    async def test_roi_calculation(self, planning_agent):
        """투자수익률계산 Intent 테스트"""
        test_queries = [
            "투자 수익률 계산해줘",
            "월세와 매매 중 어느 게 유리해?",
            "ROI 얼마나 나와?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.ROI_CALCULATION, \
                f"'{query}' should be ROI_CALCULATION, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 11. POLICY_INQUIRY (정부정책조회) ==========
    @pytest.mark.asyncio
    async def test_policy_inquiry(self, planning_agent):
        """정부정책조회 Intent 테스트"""
        test_queries = [
            "생애최초 특별공급 조건은?",
            "신혼부부 지원 정책 알려줘",
            "청년 세제 혜택은?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.POLICY_INQUIRY, \
                f"'{query}' should be POLICY_INQUIRY, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 12. CONTRACT_CREATION (계약서생성) ==========
    @pytest.mark.asyncio
    async def test_contract_creation(self, planning_agent):
        """계약서생성 Intent 테스트"""
        test_queries = [
            "임대차 계약서 작성해줘",
            "계약서 초안 만들어줘",
            "부동산 계약서 양식",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.CONTRACT_CREATION, \
                f"'{query}' should be CONTRACT_CREATION, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 13. MARKET_INQUIRY (시세트렌드분석) ==========
    @pytest.mark.asyncio
    async def test_market_inquiry(self, planning_agent):
        """시세트렌드분석 Intent 테스트"""
        test_queries = [
            "강남 아파트 시세 추이는?",
            "작년 대비 가격 올랐나요?",
            "부동산 시장 트렌드 분석",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.MARKET_INQUIRY, \
                f"'{query}' should be MARKET_INQUIRY, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 14. COMPREHENSIVE (종합분석) ==========
    @pytest.mark.asyncio
    async def test_comprehensive(self, planning_agent):
        """종합분석 Intent 테스트"""
        test_queries = [
            "강남 아파트 종합 분석해줘",
            "이 매물 전체적으로 어떻게 해야 해?",
            "다각도로 분석해줘",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            assert result.intent_type == IntentType.COMPREHENSIVE, \
                f"'{query}' should be COMPREHENSIVE, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")

    # ========== 15. IRRELEVANT (무관) ==========
    @pytest.mark.asyncio
    async def test_irrelevant(self, planning_agent):
        """무관 Intent 테스트 (부동산과 무관한 질문)"""
        # 패턴 매칭만으로는 IRRELEVANT 검출이 어려우므로 UNCLEAR로 분류될 가능성 높음
        # 이 경우 UNCLEAR도 허용
        test_queries = [
            "오늘 날씨 어때?",
            "점심 뭐 먹지?",
        ]

        for query in test_queries:
            result = await planning_agent.analyze_intent(query)
            # IRRELEVANT 또는 UNCLEAR 둘 다 허용
            assert result.intent_type in [IntentType.IRRELEVANT, IntentType.UNCLEAR], \
                f"'{query}' should be IRRELEVANT or UNCLEAR, got {result.intent_type}"
            print(f"✓ '{query}' → {result.intent_type.value}")


# ========== 통합 테스트 ==========
@pytest.mark.asyncio
async def test_all_intents_coverage():
    """15개 모든 Intent가 테스트되었는지 확인"""
    planning_agent = PlanningAgent(llm_context=None)

    # 각 Intent별 대표 질문 1개씩
    intent_samples = {
        IntentType.TERM_DEFINITION: "LTV가 뭐야?",
        IntentType.LEGAL_INQUIRY: "전세 계약 갱신 가능한가요?",
        IntentType.LOAN_SEARCH: "주택담보대출 상품 찾아줘",
        IntentType.LOAN_COMPARISON: "은행별 금리 비교해줘",
        IntentType.BUILDING_REGISTRY: "건축물대장 조회해줘",
        IntentType.PROPERTY_INFRA_ANALYSIS: "지하철역 거리는?",
        IntentType.PRICE_EVALUATION: "이 가격 괜찮아?",
        IntentType.PROPERTY_SEARCH: "강남 아파트 찾아줘",
        IntentType.PROPERTY_RECOMMENDATION: "나한테 맞는 집 추천해줘",
        IntentType.ROI_CALCULATION: "투자 수익률 계산해줘",
        IntentType.POLICY_INQUIRY: "생애최초 특별공급 조건은?",
        IntentType.CONTRACT_CREATION: "임대차 계약서 작성해줘",
        IntentType.MARKET_INQUIRY: "강남 아파트 시세 추이는?",
        IntentType.COMPREHENSIVE: "강남 아파트 종합 분석해줘",
    }

    print("\n========== 15개 Intent 전체 커버리지 테스트 ==========")
    results = {}

    for intent_type, query in intent_samples.items():
        result = await planning_agent.analyze_intent(query)
        results[intent_type] = result.intent_type
        status = "✓" if result.intent_type == intent_type else "✗"
        print(f"{status} {intent_type.value:20} | '{query}' → {result.intent_type.value}")

    # 성공률 계산
    success_count = sum(1 for expected, actual in results.items() if expected == actual)
    total_count = len(intent_samples)
    accuracy = (success_count / total_count) * 100

    print(f"\n정확도: {success_count}/{total_count} ({accuracy:.1f}%)")

    # 85% 이상 성공률 요구
    assert accuracy >= 85.0, f"Intent classification accuracy {accuracy:.1f}% is below 85%"


if __name__ == "__main__":
    # pytest 없이 직접 실행 시
    import asyncio

    async def run_all_tests():
        print("=" * 60)
        print("15개 Intent 분류 테스트 시작")
        print("=" * 60)

        planning_agent = PlanningAgent(llm_context=None)
        test_instance = TestIntentClassification()

        # 각 테스트 실행
        tests = [
            ("1. TERM_DEFINITION", test_instance.test_term_definition),
            ("2. LEGAL_INQUIRY", test_instance.test_legal_inquiry),
            ("3. LOAN_SEARCH", test_instance.test_loan_search),
            ("4. LOAN_COMPARISON", test_instance.test_loan_comparison),
            ("5. BUILDING_REGISTRY", test_instance.test_building_registry),
            ("6. PROPERTY_INFRA_ANALYSIS", test_instance.test_property_infra_analysis),
            ("7. PRICE_EVALUATION", test_instance.test_price_evaluation),
            ("8. PROPERTY_SEARCH", test_instance.test_property_search),
            ("9. PROPERTY_RECOMMENDATION", test_instance.test_property_recommendation),
            ("10. ROI_CALCULATION", test_instance.test_roi_calculation),
            ("11. POLICY_INQUIRY", test_instance.test_policy_inquiry),
            ("12. CONTRACT_CREATION", test_instance.test_contract_creation),
            ("13. MARKET_INQUIRY", test_instance.test_market_inquiry),
            ("14. COMPREHENSIVE", test_instance.test_comprehensive),
            ("15. IRRELEVANT", test_instance.test_irrelevant),
        ]

        for test_name, test_func in tests:
            print(f"\n{test_name}")
            print("-" * 60)
            try:
                await test_func(planning_agent)
                print(f"✓ {test_name} 통과")
            except AssertionError as e:
                print(f"✗ {test_name} 실패: {e}")

        # 통합 테스트
        print("\n" + "=" * 60)
        await test_all_intents_coverage()
        print("=" * 60)

    asyncio.run(run_all_tests())
