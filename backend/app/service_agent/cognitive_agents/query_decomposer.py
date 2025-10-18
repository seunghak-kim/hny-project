"""
Query Decomposer Module - 복합 질문 분해 전담
LLM을 활용하여 복합적인 사용자 질문을 독립적인 작업 단위로 분해
Phase 1 구현 - 자율적 판단 기반 (하드코딩 없음)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from app.service_agent.llm_manager import LLMService
from app.service_agent.foundation.separated_states import StandardResult

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """작업 유형 정의"""
    SEARCH = "search"           # 정보 검색
    ANALYSIS = "analysis"       # 데이터 분석
    GENERATION = "generation"   # 문서 생성
    REVIEW = "review"          # 검토/평가
    CALCULATION = "calculation" # 계산/산출
    COMPARISON = "comparison"   # 비교 분석


class ExecutionMode(Enum):
    """실행 모드"""
    SEQUENTIAL = "sequential"   # 순차 실행 (이전 결과 필요)
    PARALLEL = "parallel"      # 병렬 실행 (독립적)
    CONDITIONAL = "conditional" # 조건부 실행


@dataclass
class SubTask:
    """분해된 개별 작업"""
    task_id: str
    description: str
    task_type: TaskType
    agent_team: str  # 담당할 팀/에이전트
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)  # 선행 작업 ID들
    required_data: Dict[str, str] = field(default_factory=dict)  # 필요한 데이터
    estimated_time: float = 0.0  # 예상 소요 시간(초)
    optional: bool = False  # 선택적 작업 여부
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecomposedQuery:
    """분해된 질문 전체 구조"""
    original_query: str
    is_compound: bool
    sub_tasks: List[SubTask]
    execution_mode: ExecutionMode
    parallel_groups: List[List[str]] = field(default_factory=list)  # 병렬 실행 그룹
    total_estimated_time: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class QueryDecomposer:
    """
    복합 질문 분해기
    - LLM 자율 판단 기반
    - Few-shot learning 활용
    - Chain-of-Thought 프롬프팅
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        초기화

        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm_service = llm_service or LLMService()
        self.decomposition_examples = self._load_decomposition_examples()

    def _load_decomposition_examples(self) -> List[Dict[str, Any]]:
        """Few-shot learning을 위한 예시 로드"""
        return [
            {
                "query": "강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘",
                "tasks": [
                    {"desc": "강남구 아파트 시세 확인", "type": "search", "team": "search_team"},
                    {"desc": "대출 가능 금액 계산", "type": "calculation", "team": "analysis_team", "deps": [0]}
                ],
                "mode": "sequential"
            },
            {
                "query": "이 계약서 검토하고 위험 요소 분석해서 수정안 제시해줘",
                "tasks": [
                    {"desc": "계약서 내용 검토", "type": "review", "team": "search_team"},
                    {"desc": "위험 요소 분석", "type": "analysis", "team": "analysis_team"},
                    {"desc": "수정안 제시", "type": "generation", "team": "document_team", "deps": [0, 1]}
                ],
                "mode": "mixed"  # 1,2는 병렬, 3은 순차
            }
        ]

    async def decompose(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        intent_result: Optional[Dict[str, Any]] = None
    ) -> DecomposedQuery:
        """
        복합 질문을 개별 작업으로 분해

        Args:
            query: 원본 사용자 질문
            context: 추가 컨텍스트
            intent_result: 의도 분석 결과 (있는 경우)

        Returns:
            분해된 질문 구조
        """
        logger.info(f"Decomposing query: {query[:100]}...")

        # 단순 질문 체크
        if not self._is_compound_query(query, intent_result):
            logger.info("Query is simple, no decomposition needed")
            return self._create_simple_task(query, intent_result)

        # LLM을 통한 자율적 분해
        try:
            decomposed = await self._decompose_with_llm(query, context, intent_result)
            logger.info(f"Successfully decomposed into {len(decomposed.sub_tasks)} tasks")
            return decomposed

        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            # Fallback to simple decomposition
            return self._fallback_decomposition(query, intent_result)

    def _is_compound_query(
        self,
        query: str,
        intent_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        복합 질문 여부 판단

        Args:
            query: 사용자 질문
            intent_result: 의도 분석 결과

        Returns:
            복합 질문 여부
        """
        # Intent 분석 결과에 복합 질문 표시가 있는 경우
        if intent_result and intent_result.get("is_compound"):
            return True

        # COMPREHENSIVE 의도는 기본적으로 복합 (검색+분석 필요)
        if intent_result and intent_result.get("intent") == "COMPREHENSIVE":
            logger.debug("COMPREHENSIVE intent detected -> compound query")
            return True

        # 연결 키워드 체크
        compound_indicators = [
            "그리고", "또한", "함께", "같이", "동시에",
            "추가로", "더불어", "아울러", "그 다음",
            "하고", "해서", "한 후", "한 다음"
        ]

        query_lower = query.lower()
        for indicator in compound_indicators:
            if indicator in query_lower:
                logger.debug(f"Found compound indicator: {indicator}")
                return True

        # 해결책 요청 패턴 체크 (단순 정보 조회가 아닌 복합 처리 필요)
        solution_indicators = [
            "어떻게", "방법", "해결", "대처", "대응",
            "어찌", "어떡", "어쩌"
        ]

        for indicator in solution_indicators:
            if indicator in query_lower:
                logger.debug(f"Found solution request indicator: {indicator}")
                return True

        # 여러 동작 동사가 있는지 체크
        action_verbs = [
            "확인", "검토", "분석", "계산", "비교",
            "조회", "찾아", "알려", "만들", "작성"
        ]

        verb_count = sum(1 for verb in action_verbs if verb in query_lower)
        if verb_count >= 2:
            logger.debug(f"Multiple action verbs found: {verb_count}")
            return True

        return False

    async def _decompose_with_llm(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        intent_result: Optional[Dict[str, Any]]
    ) -> DecomposedQuery:
        """
        LLM을 활용한 자율적 질문 분해

        Args:
            query: 원본 질문
            context: 컨텍스트
            intent_result: 의도 분석 결과

        Returns:
            분해된 질문 구조
        """
        try:
            # LLM에 분해 요청
            result = await self.llm_service.complete_json_async(
                prompt_name="query_decomposition",
                variables={
                    "query": query,
                    "examples": self.decomposition_examples,
                    "intent": intent_result.get("intent") if intent_result else None,
                    "entities": intent_result.get("entities") if intent_result else {}
                },
                temperature=0.1  # 일관성 있는 분해를 위해 낮은 온도
            )

            # 결과 파싱
            sub_tasks = []
            for idx, task_data in enumerate(result.get("sub_tasks", [])):
                sub_task = SubTask(
                    task_id=f"task_{idx}",
                    description=task_data.get("description", ""),
                    task_type=self._parse_task_type(task_data.get("type", "search")),
                    agent_team=task_data.get("agent", "search_team"),
                    priority=task_data.get("priority", 1),
                    dependencies=task_data.get("depends_on", []),
                    required_data=task_data.get("required_data", {}),
                    estimated_time=task_data.get("estimated_time", 30.0),
                    optional=task_data.get("optional", False),
                    context=task_data.get("context", {})
                )
                sub_tasks.append(sub_task)

            # 실행 모드 결정
            execution_mode = self._determine_execution_mode(sub_tasks)

            # 병렬 그룹 생성
            parallel_groups = self._create_parallel_groups(sub_tasks) if execution_mode == ExecutionMode.PARALLEL else []

            return DecomposedQuery(
                original_query=query,
                is_compound=True,
                sub_tasks=sub_tasks,
                execution_mode=execution_mode,
                parallel_groups=parallel_groups,
                total_estimated_time=self._calculate_total_time(sub_tasks, execution_mode),
                confidence=result.get("confidence", 0.8),
                reasoning=result.get("reasoning", ""),
                metadata={
                    "llm_response": result,
                    "intent_result": intent_result
                }
            )

        except Exception as e:
            logger.error(f"Error in LLM decomposition: {e}")
            raise

    def _create_simple_task(
        self,
        query: str,
        intent_result: Optional[Dict[str, Any]]
    ) -> DecomposedQuery:
        """
        단순 질문에 대한 단일 작업 생성

        Args:
            query: 사용자 질문
            intent_result: 의도 분석 결과

        Returns:
            단일 작업으로 구성된 DecomposedQuery
        """
        # 의도에 따른 팀 선택
        intent = intent_result.get("intent", "UNCLEAR") if intent_result else "UNCLEAR"

        team_mapping = {
            "LEGAL_CONSULT": "search_team",
            "MARKET_INQUIRY": "search_team",
            "LOAN_CONSULT": "search_team",
            "CONTRACT_CREATION": "document_team",
            "CONTRACT_REVIEW": "analysis_team",
            "COMPREHENSIVE": "analysis_team",
            "RISK_ANALYSIS": "analysis_team",
            "UNCLEAR": "search_team"
        }

        agent_team = team_mapping.get(intent, "search_team")

        sub_task = SubTask(
            task_id="task_0",
            description=query,
            task_type=TaskType.SEARCH,
            agent_team=agent_team,
            context={"intent": intent}
        )

        return DecomposedQuery(
            original_query=query,
            is_compound=False,
            sub_tasks=[sub_task],
            execution_mode=ExecutionMode.SEQUENTIAL,
            total_estimated_time=30.0,
            confidence=1.0,
            reasoning="Simple query - no decomposition needed"
        )

    def _fallback_decomposition(
        self,
        query: str,
        intent_result: Optional[Dict[str, Any]]
    ) -> DecomposedQuery:
        """
        LLM 실패 시 기본 분해 전략

        Args:
            query: 사용자 질문
            intent_result: 의도 분석 결과

        Returns:
            기본 전략으로 분해된 질문
        """
        logger.warning("Using fallback decomposition strategy")

        # Intent 결과에서 decomposed_tasks 활용
        if intent_result and "decomposed_tasks" in intent_result:
            tasks = []
            for idx, task_desc in enumerate(intent_result["decomposed_tasks"]):
                tasks.append(SubTask(
                    task_id=f"task_{idx}",
                    description=task_desc,
                    task_type=TaskType.SEARCH,
                    agent_team="search_team",
                    priority=idx + 1
                ))

            return DecomposedQuery(
                original_query=query,
                is_compound=True,
                sub_tasks=tasks,
                execution_mode=ExecutionMode.SEQUENTIAL,
                confidence=0.5,
                reasoning="Fallback decomposition based on intent analysis"
            )

        # 최종 fallback: 단일 작업으로 처리
        return self._create_simple_task(query, intent_result)

    def _parse_task_type(self, type_str: str) -> TaskType:
        """작업 유형 문자열을 TaskType enum으로 변환"""
        type_mapping = {
            "search": TaskType.SEARCH,
            "analysis": TaskType.ANALYSIS,
            "generation": TaskType.GENERATION,
            "review": TaskType.REVIEW,
            "calculation": TaskType.CALCULATION,
            "comparison": TaskType.COMPARISON
        }
        return type_mapping.get(type_str.lower(), TaskType.SEARCH)

    def _determine_execution_mode(self, sub_tasks: List[SubTask]) -> ExecutionMode:
        """
        작업들의 의존성을 분석하여 실행 모드 결정

        Args:
            sub_tasks: 분해된 작업 목록

        Returns:
            실행 모드
        """
        # 의존성이 있는 작업이 있는지 체크
        has_dependencies = any(task.dependencies for task in sub_tasks)

        if not has_dependencies:
            # 모든 작업이 독립적이면 병렬 실행
            return ExecutionMode.PARALLEL

        # 모든 작업이 순차적인지 체크
        all_sequential = all(
            not task.dependencies or
            all(dep == f"task_{i-1}" for dep in task.dependencies)
            for i, task in enumerate(sub_tasks)
        )

        if all_sequential:
            return ExecutionMode.SEQUENTIAL

        # 혼합된 경우 (일부는 병렬, 일부는 순차)
        return ExecutionMode.CONDITIONAL

    def _create_parallel_groups(self, sub_tasks: List[SubTask]) -> List[List[str]]:
        """
        병렬 실행 가능한 작업들을 그룹화

        Args:
            sub_tasks: 분해된 작업 목록

        Returns:
            병렬 실행 그룹 리스트
        """
        groups = []
        processed = set()

        for task in sub_tasks:
            if task.task_id in processed:
                continue

            # 같은 레벨의 작업들 찾기 (동일한 의존성을 가진 작업들)
            group = [task.task_id]
            for other in sub_tasks:
                if other.task_id != task.task_id and other.task_id not in processed:
                    if task.dependencies == other.dependencies:
                        group.append(other.task_id)
                        processed.add(other.task_id)

            processed.add(task.task_id)
            groups.append(group)

        return groups

    def _calculate_total_time(
        self,
        sub_tasks: List[SubTask],
        execution_mode: ExecutionMode
    ) -> float:
        """
        전체 예상 실행 시간 계산

        Args:
            sub_tasks: 작업 목록
            execution_mode: 실행 모드

        Returns:
            예상 총 소요 시간 (초)
        """
        if execution_mode == ExecutionMode.SEQUENTIAL:
            # 순차 실행: 모든 작업 시간의 합
            return sum(task.estimated_time for task in sub_tasks)

        elif execution_mode == ExecutionMode.PARALLEL:
            # 병렬 실행: 가장 오래 걸리는 작업의 시간
            return max(task.estimated_time for task in sub_tasks) if sub_tasks else 0

        else:  # CONDITIONAL
            # 혼합: 그룹별로 계산
            # 간단히 평균값으로 추정
            total = sum(task.estimated_time for task in sub_tasks)
            return total * 0.7  # 병렬 처리로 30% 시간 단축 가정

    async def validate_decomposition(
        self,
        decomposed: DecomposedQuery
    ) -> Tuple[bool, List[str]]:
        """
        분해 결과 검증

        Args:
            decomposed: 분해된 질문 구조

        Returns:
            (유효성 여부, 오류 메시지 리스트)
        """
        errors = []

        # 작업이 비어있는지 체크
        if not decomposed.sub_tasks:
            errors.append("No sub-tasks found")

        # 순환 의존성 체크
        for task in decomposed.sub_tasks:
            if task.task_id in task.dependencies:
                errors.append(f"Circular dependency in task {task.task_id}")

        # 존재하지 않는 의존성 체크
        task_ids = {task.task_id for task in decomposed.sub_tasks}
        for task in decomposed.sub_tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    errors.append(f"Task {task.task_id} depends on non-existent task {dep}")

        # 에이전트 팀 유효성 체크
        valid_teams = ["search_team", "document_team", "analysis_team"]
        for task in decomposed.sub_tasks:
            if task.agent_team not in valid_teams:
                errors.append(f"Invalid agent team: {task.agent_team}")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"Decomposition validation failed: {errors}")

        return is_valid, errors

    def merge_results(
        self,
        sub_results: List[StandardResult]
    ) -> Dict[str, Any]:
        """
        분해된 작업들의 결과를 통합

        Args:
            sub_results: 각 작업의 결과

        Returns:
            통합된 결과
        """
        merged = {
            "status": "success",
            "sub_results": [],
            "summary": {},
            "errors": []
        }

        for result in sub_results:
            result_dict = result.to_dict()
            merged["sub_results"].append(result_dict)

            # 실패한 작업 체크
            if result.status == "failure":
                merged["status"] = "partial"
                merged["errors"].append({
                    "agent": result.agent_name,
                    "error": result.error
                })

            # 데이터 통합
            if result.data:
                merged["summary"][result.agent_name] = result.data

        # 모든 작업이 실패한 경우
        if all(r.status == "failure" for r in sub_results):
            merged["status"] = "failure"

        logger.info(f"Merged {len(sub_results)} results with status: {merged['status']}")

        return merged


# 독립 실행 가능한 헬퍼 함수들
async def decompose_query(
    query: str,
    llm_service: Optional[LLMService] = None
) -> DecomposedQuery:
    """
    간단한 인터페이스로 질문 분해

    Args:
        query: 사용자 질문
        llm_service: LLM 서비스

    Returns:
        분해된 질문
    """
    decomposer = QueryDecomposer(llm_service)
    return await decomposer.decompose(query)


def is_compound_query(query: str) -> bool:
    """
    복합 질문 여부 빠른 체크

    Args:
        query: 사용자 질문

    Returns:
        복합 질문 여부
    """
    decomposer = QueryDecomposer()
    return decomposer._is_compound_query(query, None)