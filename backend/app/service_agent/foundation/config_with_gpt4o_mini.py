"""
gpt-4o → gpt-4o-mini 전환 가이드
=====================================

config.py 수정 방법 및 A/B 테스트 전략

비용 비교:
- gpt-4o: $2.50/1M input, $10.00/1M output
- gpt-4o-mini: $0.15/1M input, $0.60/1M output
- 비용 절감: 94% (입력), 94% (출력)
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 1단계: config.py 수정
# ============================================================================

"""
파일 위치: backend/app/service_agent/foundation/config.py

기존:
```python
"models": {
    "intent_analysis": "gpt-4o-mini",
    "plan_generation": "gpt-4o-mini",
    "keyword_extraction": "gpt-4o-mini",
    "insight_generation": "gpt-4o",          # ← 변경 대상
    "response_synthesis": "gpt-4o-mini",
    "search": "gpt-4o-mini",
    "analysis": "gpt-4o"                     # ← 변경 대상
}
```

변경:
```python
"models": {
    "intent_analysis": "gpt-4o-mini",
    "plan_generation": "gpt-4o-mini",
    "keyword_extraction": "gpt-4o-mini",
    "insight_generation": "gpt-4o-mini",     # ← gpt-4o에서 변경
    "response_synthesis": "gpt-4o-mini",
    "search": "gpt-4o-mini",
    "analysis": "gpt-4o-mini"                # ← gpt-4o에서 변경
}
```
"""


# ============================================================================
# 2단계: A/B 테스트 프레임워크
# ============================================================================

class ModelABTest:
    """
    gpt-4o vs gpt-4o-mini A/B 테스트

    테스트 시나리오:
    1. 동일 쿼리로 두 모델 모두 호출
    2. 품질 비교 (사용자 평가 or 자동 평가)
    3. 비용/시간 비교
    """

    def __init__(self):
        self.test_results = []

    async def compare_models(
        self,
        query: str,
        prompt: str,
        task_type: str
    ) -> dict:
        """
        두 모델 비교

        Args:
            query: 사용자 쿼리
            prompt: LLM 프롬프트
            task_type: "insight_generation" or "analysis"

        Returns:
            비교 결과
        """
        import time
        from app.service_agent.llm_manager import LLMService

        llm_service = LLMService()

        # GPT-4o 호출
        start_4o = time.time()
        response_4o = await llm_service.generate(
            prompt=prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=500
        )
        time_4o = (time.time() - start_4o) * 1000  # ms

        # GPT-4o-mini 호출
        start_mini = time.time()
        response_mini = await llm_service.generate(
            prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=500
        )
        time_mini = (time.time() - start_mini) * 1000  # ms

        # 비용 계산 (대략적)
        token_count = len(prompt) * 2 + 500  # 입력 + 출력 추정
        cost_4o = (token_count / 1_000_000) * 6.25  # 평균 $2.50 + $10.00
        cost_mini = (token_count / 1_000_000) * 0.375  # 평균 $0.15 + $0.60

        result = {
            "query": query,
            "task_type": task_type,
            "gpt_4o": {
                "response": response_4o,
                "time_ms": time_4o,
                "cost_usd": cost_4o
            },
            "gpt_4o_mini": {
                "response": response_mini,
                "time_ms": time_mini,
                "cost_usd": cost_mini
            },
            "savings": {
                "time_reduction": (time_4o - time_mini) / time_4o * 100,
                "cost_reduction": (cost_4o - cost_mini) / cost_4o * 100
            }
        }

        self.test_results.append(result)

        logger.info(f"\n{'='*80}")
        logger.info(f"A/B Test Results: {task_type}")
        logger.info(f"{'='*80}")
        logger.info(f"Query: {query}")
        logger.info(f"\nGPT-4o:")
        logger.info(f"  Time: {time_4o:.0f}ms")
        logger.info(f"  Cost: ${cost_4o:.6f}")
        logger.info(f"  Response: {response_4o[:200]}...")
        logger.info(f"\nGPT-4o-mini:")
        logger.info(f"  Time: {time_mini:.0f}ms")
        logger.info(f"  Cost: ${cost_mini:.6f}")
        logger.info(f"  Response: {response_mini[:200]}...")
        logger.info(f"\nSavings:")
        logger.info(f"  Time: {result['savings']['time_reduction']:.1f}%")
        logger.info(f"  Cost: {result['savings']['cost_reduction']:.1f}%")
        logger.info(f"{'='*80}\n")

        return result

    def generate_report(self) -> dict:
        """테스트 결과 리포트 생성"""
        if not self.test_results:
            return {"error": "No test results"}

        avg_time_reduction = sum(
            r["savings"]["time_reduction"] for r in self.test_results
        ) / len(self.test_results)

        avg_cost_reduction = sum(
            r["savings"]["cost_reduction"] for r in self.test_results
        ) / len(self.test_results)

        total_cost_4o = sum(r["gpt_4o"]["cost_usd"] for r in self.test_results)
        total_cost_mini = sum(r["gpt_4o_mini"]["cost_usd"] for r in self.test_results)

        return {
            "total_tests": len(self.test_results),
            "average_time_reduction": f"{avg_time_reduction:.1f}%",
            "average_cost_reduction": f"{avg_cost_reduction:.1f}%",
            "total_cost_gpt4o": f"${total_cost_4o:.6f}",
            "total_cost_gpt4o_mini": f"${total_cost_mini:.6f}",
            "total_savings": f"${total_cost_4o - total_cost_mini:.6f}",
            "recommendation": self._get_recommendation(avg_cost_reduction)
        }

    def _get_recommendation(self, cost_reduction: float) -> str:
        """권장 사항 생성"""
        if cost_reduction > 90:
            return "✅ gpt-4o-mini 사용 강력 권장 (90% 이상 비용 절감)"
        elif cost_reduction > 80:
            return "✅ gpt-4o-mini 사용 권장 (80-90% 비용 절감)"
        elif cost_reduction > 70:
            return "🟡 gpt-4o-mini 고려 (70-80% 비용 절감, 품질 확인 필요)"
        else:
            return "🔴 추가 테스트 필요 (비용 절감 미미)"


# ============================================================================
# 3단계: A/B 테스트 실행 스크립트
# ============================================================================

async def run_ab_test():
    """A/B 테스트 실행"""
    test = ModelABTest()

    # 테스트 쿼리
    test_queries = [
        {
            "query": "강남구 아파트 시세 분석해줘",
            "task_type": "insight_generation"
        },
        {
            "query": "전세가율 동향을 분석하고 투자 인사이트 제공",
            "task_type": "analysis"
        },
        {
            "query": "서초구 학군 좋은 지역 추천과 이유",
            "task_type": "insight_generation"
        },
        {
            "query": "최근 부동산 시장 동향 종합 분석",
            "task_type": "analysis"
        },
        {
            "query": "신혼부부를 위한 전세 vs 매매 비교 분석",
            "task_type": "insight_generation"
        }
    ]

    # 각 쿼리로 테스트
    for test_case in test_queries:
        prompt = f"""
다음 사용자 질문에 대해 인사이트를 제공하세요:

질문: {test_case['query']}

분석 요구사항:
- 데이터 기반 인사이트
- 실용적인 조언
- 명확하고 구조화된 응답
"""
        await test.compare_models(
            query=test_case['query'],
            prompt=prompt,
            task_type=test_case['task_type']
        )

    # 최종 리포트
    report = test.generate_report()

    print("\n" + "="*80)
    print("A/B 테스트 최종 리포트")
    print("="*80)
    print(f"총 테스트: {report['total_tests']}")
    print(f"평균 시간 단축: {report['average_time_reduction']}")
    print(f"평균 비용 절감: {report['average_cost_reduction']}")
    print(f"GPT-4o 총 비용: {report['total_cost_gpt4o']}")
    print(f"GPT-4o-mini 총 비용: {report['total_cost_gpt4o_mini']}")
    print(f"총 절감액: {report['total_savings']}")
    print(f"\n권장 사항: {report['recommendation']}")
    print("="*80)

    return report


# ============================================================================
# 4단계: 품질 자동 평가 (옵션)
# ============================================================================

class QualityEvaluator:
    """응답 품질 자동 평가"""

    def __init__(self):
        self.evaluation_criteria = [
            "relevance",  # 관련성
            "completeness",  # 완전성
            "accuracy",  # 정확성
            "clarity"  # 명확성
        ]

    async def evaluate(self, response: str, ground_truth: str = None) -> dict:
        """
        응답 품질 평가

        Args:
            response: 평가할 응답
            ground_truth: 정답 (있는 경우)

        Returns:
            평가 점수
        """
        # 간단한 휴리스틱 평가
        scores = {}

        # 1. 길이 체크 (너무 짧으면 불완전)
        scores["length_score"] = min(len(response) / 500, 1.0)

        # 2. 구조 체크 (문단, 리스트 등)
        scores["structure_score"] = self._check_structure(response)

        # 3. 키워드 체크
        scores["keyword_score"] = self._check_keywords(response)

        # 4. 전체 점수
        scores["overall"] = sum(scores.values()) / len(scores)

        return scores

    def _check_structure(self, response: str) -> float:
        """구조 점수 (0-1)"""
        score = 0.0
        if "\n\n" in response:  # 문단 구분
            score += 0.3
        if any(c in response for c in ["-", "•", "1.", "2."]):  # 리스트
            score += 0.4
        if any(kw in response for kw in ["분석", "결론", "요약"]):  # 구조 키워드
            score += 0.3
        return min(score, 1.0)

    def _check_keywords(self, response: str) -> float:
        """키워드 점수 (0-1)"""
        important_keywords = ["시세", "평균", "지역", "추천", "분석"]
        found = sum(1 for kw in important_keywords if kw in response)
        return found / len(important_keywords)


# ============================================================================
# 5단계: 사용자 피드백 수집
# ============================================================================

class UserFeedbackCollector:
    """사용자 피드백 수집 및 분석"""

    def __init__(self):
        self.feedback_data = []

    def collect_feedback(
        self,
        query: str,
        response: str,
        model: str,
        rating: int,
        comments: str = None
    ):
        """
        피드백 수집

        Args:
            query: 사용자 쿼리
            response: LLM 응답
            model: 사용한 모델
            rating: 1-5 점수
            comments: 추가 코멘트
        """
        self.feedback_data.append({
            "query": query,
            "response": response[:100],
            "model": model,
            "rating": rating,
            "comments": comments,
            "timestamp": datetime.now().isoformat()
        })

    def analyze_feedback(self) -> dict:
        """피드백 분석"""
        if not self.feedback_data:
            return {"error": "No feedback data"}

        # 모델별 평균 평점
        gpt4o_ratings = [
            f["rating"] for f in self.feedback_data if f["model"] == "gpt-4o"
        ]
        mini_ratings = [
            f["rating"] for f in self.feedback_data if f["model"] == "gpt-4o-mini"
        ]

        return {
            "total_feedback": len(self.feedback_data),
            "gpt4o": {
                "count": len(gpt4o_ratings),
                "avg_rating": sum(gpt4o_ratings) / len(gpt4o_ratings) if gpt4o_ratings else 0
            },
            "gpt4o_mini": {
                "count": len(mini_ratings),
                "avg_rating": sum(mini_ratings) / len(mini_ratings) if mini_ratings else 0
            },
            "quality_difference": self._calculate_quality_diff(gpt4o_ratings, mini_ratings)
        }

    def _calculate_quality_diff(self, ratings1: list, ratings2: list) -> str:
        """품질 차이 계산"""
        if not ratings1 or not ratings2:
            return "N/A"

        avg1 = sum(ratings1) / len(ratings1)
        avg2 = sum(ratings2) / len(ratings2)
        diff = avg1 - avg2

        if abs(diff) < 0.2:
            return "동등 (차이 미미)"
        elif diff > 0:
            return f"gpt-4o가 {diff:.1f}점 더 높음"
        else:
            return f"gpt-4o-mini가 {abs(diff):.1f}점 더 높음"


# ============================================================================
# 6단계: 전환 체크리스트
# ============================================================================

"""
gpt-4o → gpt-4o-mini 전환 체크리스트:

Phase 1: 준비 (1-2일)
□ A/B 테스트 스크립트 작성
□ 테스트 쿼리 준비 (최소 20-30개)
□ 평가 기준 정의

Phase 2: 테스트 (1주)
□ A/B 테스트 실행
□ 응답 품질 비교
□ 비용/시간 측정
□ 사용자 피드백 수집 (가능하면)

Phase 3: 분석 (2-3일)
□ 품질 차이 분석
□ 비용 절감액 계산
□ ROI 계산
□ 의사결정

Phase 4: 적용 (1일)
□ config.py 수정
□ 배포
□ 모니터링 설정

Phase 5: 모니터링 (1-2주)
□ 품질 모니터링
□ 사용자 피드백 추적
□ 필요 시 롤백

예상 결과:
✅ 비용 절감: 80-94% (입력/출력 토큰에 따라)
✅ 품질: 95% 이상 동등 (대부분의 작업에서)
🟡 롤백 가능성: <5% (품질 이슈 발생 시)
"""


# ============================================================================
# 실행 예시
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def main():
        # A/B 테스트 실행
        print("Starting A/B Test...")
        report = await run_ab_test()

        # 추가 분석
        print("\nQuality Evaluation...")
        evaluator = QualityEvaluator()
        # ... 품질 평가 로직

    asyncio.run(main())
