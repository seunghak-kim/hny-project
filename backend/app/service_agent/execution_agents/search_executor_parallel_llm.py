"""
LLM 호출 병렬화 구현 가이드
============================

현재 문제:
- 도구 선택 (1-2초) → 파라미터 추출 (1-2초) → 키워드 추출 (1초) = 순차 실행
- 총 3-5초 소요

개선 방안:
- 독립적인 LLM 호출은 병렬 실행
- 의존성 있는 호출만 순차 실행
- asyncio.gather() 사용

예상 효과:
- LLM 호출 시간: 3-5초 → 1.5-2.5초 (40-50% 단축)
- 전체 응답 시간: 7.05초 → 5.0-5.5초 (추가 20-30% 단축)
"""

import asyncio
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# 현재 구조 (순차 실행)
# ============================================================================

class CurrentSequentialFlow:
    """현재 순차 실행 구조"""

    async def execute_search(self, query: str) -> Dict[str, Any]:
        """
        현재: 순차 실행

        Timeline:
        [0-1s]    도구 선택 LLM 호출
        [1-2s]    파라미터 추출 LLM 호출
        [2-3s]    키워드 추출 LLM 호출
        [3-7s]    실제 검색 수행

        총 7초
        """
        # 1단계: 도구 선택 (1-2초)
        selected_tools = await self._select_tools_with_llm(query)

        # 2단계: 파라미터 추출 (1-2초)
        params = await self._extract_parameters_with_llm(query, selected_tools)

        # 3단계: 키워드 추출 (1초)
        keywords = await self._extract_keywords_with_llm(query)

        # 4단계: 검색 수행
        results = await self._perform_search(selected_tools, params, keywords)

        return results


# ============================================================================
# 개선 구조 (병렬 실행)
# ============================================================================

class ImprovedParallelFlow:
    """개선된 병렬 실행 구조"""

    async def execute_search(self, query: str) -> Dict[str, Any]:
        """
        개선: 병렬 실행

        Timeline:
        [0-2s]    도구 선택 + 키워드 추출 (병렬)
        [2-3s]    파라미터 추출 (도구 선택 결과 필요)
        [3-7s]    실제 검색 수행

        총 5초 (2초 단축)
        """
        # ⭐ Phase 1: 독립적인 작업 병렬 실행
        selected_tools, keywords = await asyncio.gather(
            self._select_tools_with_llm(query),
            self._extract_keywords_with_llm(query)
        )

        # Phase 2: 도구별 파라미터 추출 (선택된 도구에 따라 실행)
        params = await self._extract_parameters_with_llm(query, selected_tools)

        # Phase 3: 검색 수행
        results = await self._perform_search(selected_tools, params, keywords)

        return results


# ============================================================================
# 고급 병렬화 구조 (도구별 파라미터 추출도 병렬)
# ============================================================================

class AdvancedParallelFlow:
    """고급 병렬 실행 구조"""

    async def execute_search(self, query: str) -> Dict[str, Any]:
        """
        고급: 최대 병렬화

        Timeline:
        [0-2s]    도구 선택 + 키워드 추출 (병렬)
        [2-3s]    도구별 파라미터 추출 (병렬)
        [3-7s]    실제 검색 수행 (병렬)

        총 4.5초 (2.5초 단축)
        """
        # Phase 1: 독립적인 작업 병렬 실행
        selected_tools, keywords = await asyncio.gather(
            self._select_tools_with_llm(query),
            self._extract_keywords_with_llm(query)
        )

        # ⭐ Phase 2: 도구별 파라미터 추출 병렬 실행
        param_tasks = [
            self._extract_parameters_with_llm(query, tool)
            for tool in selected_tools
        ]
        params_list = await asyncio.gather(*param_tasks)

        # 도구별 파라미터 매핑
        params_by_tool = dict(zip(selected_tools, params_list))

        # ⭐ Phase 3: 검색 병렬 수행
        search_tasks = [
            self._search_with_tool(tool, params_by_tool[tool])
            for tool in selected_tools
        ]
        search_results = await asyncio.gather(*search_tasks)

        # 결과 통합
        results = self._aggregate_results(search_results, keywords)

        return results


# ============================================================================
# 실제 SearchExecutor 수정 방법
# ============================================================================

"""
파일: backend/app/service_agent/execution_agents/search_executor.py

수정 위치: prepare_search_node 메서드 또는 execute 메서드
"""


async def prepare_search_node_parallel(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    검색 준비 노드 (병렬화 버전)

    기존:
        1. 키워드 추출
        2. 도구 선택
        3. 파라미터 추출
        (순차 실행: 3-5초)

    개선:
        1. 키워드 추출 + 도구 선택 (병렬)
        2. 파라미터 추출
        (병렬 실행: 2-3초)
    """
    query = state.get("query") or state.get("user_query")

    if not query:
        logger.error("No query provided in state")
        state["status"] = "failed"
        state["error"] = "Query is required"
        return state

    try:
        # ⭐ Phase 1: 독립적인 LLM 호출 병렬 실행
        logger.info("🚀 Starting parallel LLM calls...")

        start_time = asyncio.get_event_loop().time()

        # 병렬 실행: 키워드 추출 + 도구 선택
        keywords_task = asyncio.create_task(
            self._extract_keywords_with_llm(query)
        )
        tools_task = asyncio.create_task(
            self._select_tools_with_llm(query)
        )

        # 결과 대기
        keywords, tool_selection_result = await asyncio.gather(
            keywords_task,
            tools_task,
            return_exceptions=True  # 에러 발생 시에도 계속 진행
        )

        parallel_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"✅ Parallel LLM calls completed in {parallel_time*1000:.0f}ms")

        # 에러 처리
        if isinstance(keywords, Exception):
            logger.error(f"Keyword extraction failed: {keywords}")
            keywords = self._extract_keywords_with_fallback(query)

        if isinstance(tool_selection_result, Exception):
            logger.error(f"Tool selection failed: {tool_selection_result}")
            tool_selection_result = self._select_tools_with_fallback(query=query)

        # State 업데이트
        state["keywords"] = keywords
        state["selected_tools"] = tool_selection_result.get("selected_tools", [])
        state["tool_selection_confidence"] = tool_selection_result.get("confidence", 0.0)
        state["tool_selection_reasoning"] = tool_selection_result.get("reasoning", "")

        # Phase 2: 파라미터 추출 (도구 선택 결과 필요)
        # 각 도구별로 병렬 실행 가능
        selected_tools = state["selected_tools"]

        if selected_tools:
            param_tasks = [
                self._extract_parameters_with_llm(query, tool)
                for tool in selected_tools
            ]

            params_list = await asyncio.gather(*param_tasks, return_exceptions=True)

            # 도구별 파라미터 매핑
            params_by_tool = {}
            for tool, params in zip(selected_tools, params_list):
                if isinstance(params, Exception):
                    logger.error(f"Parameter extraction failed for {tool}: {params}")
                    params_by_tool[tool] = {}
                else:
                    params_by_tool[tool] = params

            state["params_by_tool"] = params_by_tool

        state["status"] = "prepared"
        return state

    except Exception as e:
        logger.error(f"Search preparation failed: {e}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        return state


# ============================================================================
# 검색 실행 병렬화
# ============================================================================

async def execute_search_node_parallel(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    검색 실행 노드 (병렬화 버전)

    기존:
        legal_search → market_data → real_estate_search (순차)
        (2-4초)

    개선:
        legal_search + market_data + real_estate_search (병렬)
        (1-2초)
    """
    selected_tools = state.get("selected_tools", [])
    params_by_tool = state.get("params_by_tool", {})

    if not selected_tools:
        logger.warning("No tools selected, skipping search")
        state["status"] = "completed"
        return state

    try:
        # ⭐ 모든 검색 도구 병렬 실행
        search_tasks = []

        for tool_name in selected_tools:
            params = params_by_tool.get(tool_name, {})

            if tool_name == "legal_search":
                task = self._search_legal(state.get("query"), params)
            elif tool_name == "market_data":
                task = self._search_market_data(state.get("query"), params)
            elif tool_name == "real_estate_search":
                task = self._search_real_estate(state.get("query"), params)
            elif tool_name == "loan_data":
                task = self._search_loan_data(state.get("query"), params)
            elif tool_name == "infrastructure":
                task = self._search_infrastructure(state.get("query"), params)
            elif tool_name == "building_registry":
                task = self._search_building_registry(state.get("query"), params)
            else:
                continue

            search_tasks.append((tool_name, task))

        # 병렬 실행
        logger.info(f"🚀 Starting {len(search_tasks)} parallel searches...")
        start_time = asyncio.get_event_loop().time()

        results = await asyncio.gather(
            *[task for _, task in search_tasks],
            return_exceptions=True
        )

        parallel_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"✅ Parallel searches completed in {parallel_time*1000:.0f}ms")

        # 결과 처리
        for (tool_name, _), result in zip(search_tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Search failed for {tool_name}: {result}")
                state[f"{tool_name}_results"] = []
            else:
                state[f"{tool_name}_results"] = result

        state["status"] = "completed"
        return state

    except Exception as e:
        logger.error(f"Search execution failed: {e}", exc_info=True)
        state["status"] = "failed"
        state["error"] = str(e)
        return state


# ============================================================================
# 성능 비교 분석
# ============================================================================

class PerformanceComparison:
    """순차 vs 병렬 성능 비교"""

    @staticmethod
    def calculate_improvement():
        """
        성능 개선 계산

        순차 실행:
        ├─ 도구 선택: 1.5초
        ├─ 키워드 추출: 1.0초
        ├─ 파라미터 추출: 1.0초 × 3개 도구 = 3.0초
        ├─ 검색 실행: 0.5초 × 3개 도구 = 1.5초
        └─ 총: 7.0초

        병렬 실행:
        ├─ 도구 선택 + 키워드 추출: max(1.5, 1.0) = 1.5초 (병렬)
        ├─ 파라미터 추출: 1.0초 (3개 도구 병렬)
        ├─ 검색 실행: 0.5초 (3개 도구 병렬)
        └─ 총: 3.0초

        개선:
        ├─ 시간 단축: 7.0s → 3.0s (57% 단축)
        ├─ LLM 호출 개수: 동일 (비용 동일)
        └─ 동시성: 최대 3개 작업 병렬
        """

        sequential = {
            "tool_selection": 1.5,
            "keyword_extraction": 1.0,
            "param_extraction": 3.0,  # 3 tools × 1.0s each
            "search_execution": 1.5,  # 3 tools × 0.5s each
            "total": 7.0
        }

        parallel = {
            "phase1_parallel": 1.5,  # max(tool_selection, keyword_extraction)
            "phase2_parallel": 1.0,  # 3 tools in parallel
            "phase3_parallel": 0.5,  # 3 tools in parallel
            "total": 3.0
        }

        improvement = {
            "time_saved": sequential["total"] - parallel["total"],
            "percentage": (sequential["total"] - parallel["total"]) / sequential["total"] * 100,
            "speedup": sequential["total"] / parallel["total"]
        }

        return sequential, parallel, improvement


# ============================================================================
# 에러 처리 전략
# ============================================================================

class ErrorHandlingStrategy:
    """병렬 실행 시 에러 처리"""

    @staticmethod
    async def safe_parallel_execution(tasks: List[asyncio.Task]) -> List[Any]:
        """
        안전한 병렬 실행

        전략:
        1. return_exceptions=True 사용
        2. 일부 실패해도 나머지 작업 계속 진행
        3. 실패한 작업은 fallback으로 처리
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed: {result}")
                processed_results.append(None)  # or fallback value
            else:
                processed_results.append(result)

        return processed_results

    @staticmethod
    async def timeout_protection(task: asyncio.Task, timeout: float = 5.0):
        """
        타임아웃 보호

        LLM 호출이 너무 오래 걸리면 취소
        """
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Task timed out after {timeout}s")
            return None


# ============================================================================
# 적용 체크리스트
# ============================================================================

"""
병렬화 적용 체크리스트:

Phase 1: 준비 (1일)
□ 의존성 분석 (어떤 LLM 호출이 독립적인가?)
□ 병렬화 가능 지점 식별
□ 에러 처리 전략 수립

Phase 2: 구현 (2-3일)
□ prepare_search_node 병렬화
□ execute_search_node 병렬화
□ 에러 처리 추가
□ 타임아웃 보호 추가

Phase 3: 테스트 (2일)
□ 기능 테스트 (순차와 동일한 결과)
□ 성능 테스트 (시간 측정)
□ 에러 시나리오 테스트
□ 부하 테스트

Phase 4: 배포 (1일)
□ 프로덕션 배포
□ 모니터링
□ 롤백 준비

예상 결과:
✅ 응답 시간: 7.0s → 3.0-4.0s (40-57% 단축)
✅ 비용: 동일 (LLM 호출 횟수 동일)
✅ 사용자 경험: 크게 개선
⚠️ 동시성 증가: 서버 리소스 모니터링 필요
"""


# ============================================================================
# 실행 예시
# ============================================================================

if __name__ == "__main__":
    # 성능 비교
    seq, par, imp = PerformanceComparison.calculate_improvement()

    print("="*80)
    print("LLM 호출 병렬화 성능 비교")
    print("="*80)
    print(f"\n순차 실행 (현재):")
    print(f"  도구 선택: {seq['tool_selection']:.1f}s")
    print(f"  키워드 추출: {seq['keyword_extraction']:.1f}s")
    print(f"  파라미터 추출: {seq['param_extraction']:.1f}s")
    print(f"  검색 실행: {seq['search_execution']:.1f}s")
    print(f"  총 시간: {seq['total']:.1f}s")

    print(f"\n병렬 실행 (개선):")
    print(f"  Phase 1 (병렬): {par['phase1_parallel']:.1f}s")
    print(f"  Phase 2 (병렬): {par['phase2_parallel']:.1f}s")
    print(f"  Phase 3 (병렬): {par['phase3_parallel']:.1f}s")
    print(f"  총 시간: {par['total']:.1f}s")

    print(f"\n개선 효과:")
    print(f"  절약 시간: {imp['time_saved']:.1f}s")
    print(f"  단축률: {imp['percentage']:.1f}%")
    print(f"  속도 향상: {imp['speedup']:.1f}x")
    print("="*80)
