"""
Planning Agent - 의도 분석 및 실행 계획 수립 전담
Supervisor의 계획 관련 로직을 분리하여 독립적으로 관리
Phase 1 Enhancement: Query Decomposer 통합
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Path setup
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import AgentAdapter
from app.service_agent.llm_manager import LLMService
from app.service_agent.cognitive_agents.query_decomposer import (
    QueryDecomposer,
    DecomposedQuery,
    ExecutionMode as DecomposerExecutionMode
)

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """의도 타입 정의 (15개 카테고리)"""
    TERM_DEFINITION = "용어설명"
    LEGAL_INQUIRY = "법률해설"
    LOAN_SEARCH = "대출상품검색"
    LOAN_COMPARISON = "대출조건비교"
    BUILDING_REGISTRY = "건축물대장조회"
    PROPERTY_INFRA_ANALYSIS = "매물인프라분석"
    PRICE_EVALUATION = "가격평가"
    PROPERTY_SEARCH = "매물검색"
    PROPERTY_RECOMMENDATION = "맞춤추천"
    ROI_CALCULATION = "투자수익률계산"
    POLICY_INQUIRY = "정부정책조회"
    CONTRACT_CREATION = "계약서생성"
    MARKET_INQUIRY = "시세트렌드분석"
    COMPREHENSIVE = "종합분석"
    IRRELEVANT = "무관"
    UNCLEAR = "unclear"
    ERROR = "error"


class ExecutionStrategy(Enum):
    """실행 전략"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


@dataclass
class IntentResult:
    """의도 분석 결과"""
    intent_type: IntentType
    confidence: float
    keywords: List[str] = field(default_factory=list)
    reasoning: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    suggested_agents: List[str] = field(default_factory=list)
    fallback: bool = False


@dataclass
class ExecutionStep:
    """실행 단계"""
    agent_name: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 1
    optional: bool = False


@dataclass
class ExecutionPlan:
    """실행 계획"""
    steps: List[ExecutionStep]
    strategy: ExecutionStrategy
    intent: IntentResult
    estimated_time: float = 0.0
    parallel_groups: List[List[str]] = field(default_factory=list)
    error_handling: str = "continue"  # continue, stop, rollback
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlanningAgent:
    """
    의도 분석 및 실행 계획 수립을 전담하는 Agent
    """

    def __init__(self, llm_context=None):
        """
        초기화

        Args:
            llm_context: LLM Context (Optional)
        """
        self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
        self.intent_patterns = self._initialize_intent_patterns()
        self.agent_capabilities = self._load_agent_capabilities()
        # Phase 1: Query Decomposer 추가
        self.query_decomposer = QueryDecomposer(self.llm_service)

    def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """의도 패턴 초기화 - 15개 카테고리"""
        return {
            IntentType.TERM_DEFINITION: [
                "뭐야", "무엇", "의미", "설명", "개념", "정의", "차이", "란",
                "LTV", "대항력", "분양권", "입주권", "재건축", "재개발", "DSR"
            ],
            IntentType.LEGAL_INQUIRY: [
                "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신", "가능한가요",
                "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
                "주택임대차보호법", "확정일자", "대항력", "인상", "계약금", "위약금", "등기", "청약", "당첨"
            ],
            IntentType.LOAN_SEARCH: [
                "대출", "상품", "찾다", "어떤 게", "주택담보대출", "전세자금대출",
                "신생아 특례", "청년", "은행"
            ],
            IntentType.LOAN_COMPARISON: [
                "비교", "금리", "한도", "조건", "유리", "어느", "은행별",
                "DSR", "LTV", "DTI"
            ],
            IntentType.BUILDING_REGISTRY: [
                "건축물대장", "건물정보", "준공", "용도", "면적", "조회",
                "불법 증축", "주차장", "세대수"
            ],
            IntentType.PROPERTY_INFRA_ANALYSIS: [
                "지하철", "마트", "병원", "약국", "초등학교", "중학교", "고등학교",
                "학군", "인프라", "근처", "주변", "도보권", "거리", "교통", "편의시설"
            ],
            IntentType.PRICE_EVALUATION: [
                "적정가", "가격 평가", "괜찮아", "비싸", "저렴", "유사 매물",
                "적정한가요", "합리적", "평가"
            ],
            IntentType.PROPERTY_SEARCH: [
                "찾다", "검색", "구하다", "원하다", "방", "아파트", "오피스텔", "빌라",
                "원룸", "매물", "리스트"
            ],
            IntentType.PROPERTY_RECOMMENDATION: [
                "추천", "제안", "적합", "좋은", "맞춤", "어디",
                "나한테 맞는", "신혼부부", "학군", "투자"
            ],
            IntentType.ROI_CALCULATION: [
                "투자", "수익률", "ROI", "계산", "유리", "손익",
                "월세", "매매", "전세"
            ],
            IntentType.POLICY_INQUIRY: [
                "특별공급", "생애최초", "신혼부부", "청년", "지원", "정책", "혜택",
                "다자녀", "세제", "감면"
            ],
            IntentType.CONTRACT_CREATION: [
                "작성", "만들", "생성", "초안", "계약서",
                "써줘", "만들어줘", "작성해줘", "양식"
            ],
            IntentType.MARKET_INQUIRY: [
                "시세", "추이", "트렌드", "거래 동향", "올랐나요", "떨어졌나요",
                "변화", "상승", "하락", "시장", "분위기", "전월 대비", "작년 대비"
            ],
            IntentType.COMPREHENSIVE: [
                "종합", "전체", "모든", "복합적", "다각도", "어떻게 해야", "고민",
                "분석", "추천", "해결", "대처", "도움", "조언"
            ]
        }

    def _load_agent_capabilities(self) -> Dict[str, Any]:
        """Agent 능력 정보 로드"""
        capabilities = {}
        for agent_name in AgentRegistry.list_agents():
            agent_caps = AgentRegistry.get_capabilities(agent_name)
            if agent_caps:
                capabilities[agent_name] = agent_caps
        return capabilities

    async def analyze_intent(self, query: str, context: Optional[Dict] = None) -> IntentResult:
        """
        사용자 의도 분석

        Args:
            query: 사용자 쿼리
            context: 추가 컨텍스트

        Returns:
            의도 분석 결과
        """
        logger.info(f"Analyzing intent for query: {query[:100]}...")

        # LLM을 사용한 분석 (가능한 경우)
        if self.llm_service:
            try:
                return await self._analyze_with_llm(query, context)
            except Exception as e:
                logger.warning(f"LLM analysis failed, falling back to pattern matching: {e}")

        # 패턴 매칭 기반 분석 (fallback)
        return self._analyze_with_patterns(query, context)

    async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
        """LLM을 사용한 의도 분석 (LLMService 사용)"""
        try:
            # Context에서 chat_history 추출
            chat_history = context.get("chat_history", []) if context else []

            # Chat history를 문자열로 포맷팅
            chat_history_text = ""
            if chat_history:
                formatted_history = []
                for msg in chat_history:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if role == "user":
                        formatted_history.append(f"사용자: {content}")
                    elif role == "assistant":
                        formatted_history.append(f"AI: {content}")

                if formatted_history:
                    chat_history_text = "\n".join(formatted_history)

            # LLMService를 통한 의도 분석
            result = await self.llm_service.complete_json_async(
                prompt_name="intent_analysis",
                variables={
                    "query": query,
                    "chat_history": chat_history_text
                },
                temperature=0.0,  # 더 빠른 샘플링 (deterministic)
                max_tokens=500    # 불필요하게 긴 reasoning 방지
            )

            # JSON 직렬화하여 로깅 (object object 출력 방지)
            logger.info(f"LLM Intent Analysis Result: {json.dumps(result, ensure_ascii=False)}")

            # Intent 타입 파싱
            intent_str = result.get("intent", "UNCLEAR").upper()
            try:
                intent_type = IntentType[intent_str]
            except KeyError:
                logger.warning(f"Unknown intent type from LLM: {intent_str}, using UNCLEAR")
                intent_type = IntentType.UNCLEAR

            # Agent 선택 (IRRELEVANT/UNCLEAR은 생략하여 성능 최적화)
            if intent_type in [IntentType.IRRELEVANT, IntentType.UNCLEAR]:
                suggested_agents = []
                logger.info(f"⚡ Skipping agent selection for {intent_type.value} (performance optimization)")
            else:
                suggested_agents = await self._suggest_agents(
                    intent_type=intent_type,
                    query=query,
                    keywords=result.get("keywords", [])
                )

            # 🆕 reuse_previous_data를 entities에 추가
            entities = result.get("entities", {})
            reuse_previous_data = result.get("reuse_previous_data", False)

            # entities에 reuse_previous_data 추가 (team_supervisor에서 사용하기 위해)
            if reuse_previous_data:
                entities["reuse_previous_data"] = reuse_previous_data

            return IntentResult(
                intent_type=intent_type,
                confidence=result.get("confidence", 0.5),
                keywords=result.get("keywords", []),
                reasoning=result.get("reasoning", ""),
                entities=entities,  # reuse_previous_data가 포함된 entities
                suggested_agents=suggested_agents,
                fallback=False
            )

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            raise

    def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
        """패턴 매칭 기반 의도 분석"""
        detected_intents = {}
        found_keywords = []

        # 각 의도 타입별 점수 계산
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in query.lower():
                    score += 1
                    found_keywords.append(pattern)
            if score > 0:
                detected_intents[intent_type] = score

        # 가장 높은 점수의 의도 선택
        if detected_intents:
            best_intent = max(detected_intents.items(), key=lambda x: x[1])
            intent_type = best_intent[0]
            confidence = min(best_intent[1] * 0.3, 1.0)
        else:
            intent_type = IntentType.UNCLEAR
            confidence = 0.0

        # Agent 선택 (패턴 매칭 - fallback에서는 기본 Agent 사용)
        # Note: This is sync function now, so we provide basic agent selection
        intent_to_agent = {
            IntentType.TERM_DEFINITION: ["search_team"],
            IntentType.LEGAL_INQUIRY: ["search_team"],
            IntentType.LOAN_SEARCH: ["search_team"],
            IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
            IntentType.BUILDING_REGISTRY: ["search_team"],
            IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
            IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
            IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
            IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
            IntentType.ROI_CALCULATION: ["analysis_team"],
            IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
            IntentType.CONTRACT_CREATION: ["document_team"],
            IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
            IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
            IntentType.UNCLEAR: ["search_team"],
        }
        suggested_agents = intent_to_agent.get(intent_type, ["search_team"])

        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            keywords=found_keywords,
            reasoning="Pattern-based analysis",
            suggested_agents=suggested_agents,
            fallback=True
        )

    async def _suggest_agents(
        self,
        intent_type: IntentType,
        query: str,
        keywords: List[str]
    ) -> List[str]:
        """
        LLM 기반 Agent 추천 - 다층 Fallback 전략 + 키워드 필터

        Args:
            intent_type: 분석된 의도 타입
            query: 원본 쿼리
            keywords: 추출된 키워드

        Returns:
            추천 Agent 목록
        """
        # === 0차: 키워드 기반 필터 (경계 케이스 해결) ===
        # LEGAL_INQUIRY: 단순 질문은 search만, 복잡한 질문은 search + analysis
        if intent_type == IntentType.LEGAL_INQUIRY:
            # 분석이 필요한 키워드
            analysis_keywords = [
                "비교", "분석", "계산", "평가", "추천", "검토",
                "어떻게", "방법", "차이", "장단점", "괜찮아",
                "해야", "대응", "해결", "조치", "문제"
            ]

            needs_analysis = any(kw in query for kw in analysis_keywords)

            if not needs_analysis:
                logger.info(f"✅ LEGAL_INQUIRY without analysis keywords → search_team only")
                return ["search_team"]
            else:
                logger.info(f"✅ LEGAL_INQUIRY with analysis keywords → search + analysis")
                return ["search_team", "analysis_team"]

        # MARKET_INQUIRY: 비교/분석 키워드 체크
        if intent_type == IntentType.MARKET_INQUIRY:
            analysis_keywords = ["비교", "분석", "평가", "추천", "차이", "장단점"]
            needs_analysis = any(kw in query for kw in analysis_keywords)

            if not needs_analysis:
                logger.info(f"✅ MARKET_INQUIRY without analysis keywords → search_team only")
                return ["search_team"]

        # === 1차: Primary LLM으로 Agent 선택 ===
        if self.llm_service:
            try:
                agents = await self._select_agents_with_llm(
                    intent_type=intent_type,
                    query=query,
                    keywords=keywords,
                    attempt=1
                )
                if agents:
                    logger.info(f"✅ Primary LLM selected agents: {agents}")
                    return agents
            except Exception as e:
                logger.warning(f"⚠️ Primary LLM agent selection failed: {e}")

        # === 2차: Simplified prompt retry ===
        if self.llm_service:
            try:
                agents = await self._select_agents_with_llm_simple(
                    intent_type=intent_type,
                    query=query
                )
                if agents:
                    logger.info(f"✅ Simplified LLM selected agents: {agents}")
                    return agents
            except Exception as e:
                logger.warning(f"⚠️ Simplified LLM agent selection failed: {e}")

        # === 3차: Safe default agents (모든 작업 처리 가능한 조합) ===
        logger.error("⚠️ All LLM attempts failed, using safe default agents")

        # Intent에 따른 안전한 기본값 (15개 카테고리)
        safe_defaults = {
            IntentType.TERM_DEFINITION: ["search_team"],
            IntentType.LEGAL_INQUIRY: ["search_team"],
            IntentType.LOAN_SEARCH: ["search_team"],
            IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
            IntentType.BUILDING_REGISTRY: ["search_team"],
            IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
            IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
            IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
            IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
            IntentType.ROI_CALCULATION: ["analysis_team"],
            IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
            IntentType.CONTRACT_CREATION: ["document_team"],
            IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
            IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
            IntentType.IRRELEVANT: ["search_team"],
            IntentType.UNCLEAR: ["search_team", "analysis_team"],  # 포괄적 대응
            IntentType.ERROR: ["search_team", "analysis_team"]
        }

        result = safe_defaults.get(intent_type, ["search_team", "analysis_team"])
        logger.info(f"Safe default agents for {intent_type.value}: {result}")
        return result

    async def _select_agents_with_llm(
        self,
        intent_type: IntentType,
        query: str,
        keywords: List[str],
        attempt: int = 1
    ) -> List[str]:
        """
        LLM을 사용한 Agent 선택 (상세 버전)

        Args:
            intent_type: 의도 타입
            query: 원본 쿼리
            keywords: 키워드 목록
            attempt: 시도 횟수

        Returns:
            선택된 Agent 목록
        """
        # 사용 가능한 Agent 정보 수집
        available_agents = {
            "search_team": {
                "name": "search_team",
                "capabilities": "법률 검색, 용어 설명, 부동산 시세 조회, 개별 매물 검색, 대출 상품 검색, 건축물대장 조회, 정부 정책 조회",
                "tools": ["realestate_terminology", "legal_search", "market_data", "real_estate_search", "loan_data", "building_registry", "policy_matcher"],
                "use_cases": [
                    "용어설명", "법률해설", "대출상품검색", "건축물대장조회", "정부정책조회", "매물검색"
                ]
            },
            "analysis_team": {
                "name": "analysis_team",
                "capabilities": "데이터 분석, 가격 평가, 인프라 분석, 투자 수익률 계산, 리스크 평가, 추천",
                "tools": ["contract_analysis", "market_analysis", "roi_calculator", "infrastructure", "loan_simulator"],
                "use_cases": [
                    "대출조건비교", "매물인프라분석", "가격평가", "매물검색",
                    "맞춤추천", "투자수익률계산", "종합분석"
                ]
            },
            "document_team": {
                "name": "document_team",
                "capabilities": "계약서 작성, 문서 생성, 문서 검토",
                "tools": ["lease_contract_generator"],
                "use_cases": ["계약서생성"]
            }
        }

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="agent_selection",
                variables={
                    "query": query,
                    "intent_type": intent_type.value,
                    "keywords": keywords,
                    "available_agents": available_agents,
                    "attempt": attempt
                },
                temperature=0.1 if attempt == 1 else 0.3  # 재시도 시 더 유연하게
            )

            selected = result.get("selected_agents", [])
            reasoning = result.get("reasoning", "")

            logger.info(f"LLM agent selection reasoning: {reasoning}")

            # 유효성 검사
            valid_agents = [a for a in selected if a in available_agents]

            if not valid_agents:
                logger.warning("LLM returned no valid agents")
                return []

            return valid_agents

        except Exception as e:
            logger.error(f"LLM agent selection failed: {e}")
            raise

    async def _select_agents_with_llm_simple(
        self,
        intent_type: IntentType,
        query: str
    ) -> List[str]:
        """
        LLM을 사용한 Agent 선택 (간소화 버전)
        Primary 실패 시 더 간단한 프롬프트로 재시도
        """
        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="agent_selection_simple",
                variables={
                    "query": query,
                    "intent_type": intent_type.value
                },
                temperature=0.3
            )

            selected = result.get("agents", [])

            # 간단한 유효성 검사
            valid_teams = ["search_team", "analysis_team", "document_team"]
            valid_agents = [a for a in selected if a in valid_teams]

            return valid_agents

        except Exception as e:
            logger.error(f"Simple LLM agent selection failed: {e}")
            raise

    async def create_comprehensive_plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Phase 1 Enhancement: 복합 질문 분해를 포함한 종합 계획 수립

        Args:
            query: 사용자 질문
            context: 추가 컨텍스트

        Returns:
            종합 실행 계획
        """
        logger.info(f"Creating comprehensive plan for query: {query[:100]}...")

        # 1. 의도 분석
        intent = await self.analyze_intent(query, context)
        logger.info(f"Intent analyzed: {intent.intent_type.value} (confidence: {intent.confidence:.2f})")

        # 2. 복합 질문 분해
        decomposed = await self.query_decomposer.decompose(
            query=query,
            context=context,
            intent_result={
                "intent": intent.intent_type.value,
                "confidence": intent.confidence,
                "keywords": intent.keywords,
                "entities": intent.entities,
                "is_compound": len(intent.suggested_agents) > 1
            }
        )
        logger.info(f"Query decomposed into {len(decomposed.sub_tasks)} tasks")

        # 3. 분해된 작업을 기반으로 실행 계획 생성
        if decomposed.is_compound:
            # 복합 질문: 분해된 작업들로 계획 수립
            steps = []
            for task in decomposed.sub_tasks:
                step = ExecutionStep(
                    agent_name=task.agent_team,
                    priority=task.priority,
                    dependencies=task.dependencies,
                    input_mapping=task.required_data,
                    timeout=int(task.estimated_time),
                    optional=task.optional
                )
                steps.append(step)

            # 실행 전략 변환
            strategy_map = {
                DecomposerExecutionMode.SEQUENTIAL: ExecutionStrategy.SEQUENTIAL,
                DecomposerExecutionMode.PARALLEL: ExecutionStrategy.PARALLEL,
                DecomposerExecutionMode.CONDITIONAL: ExecutionStrategy.CONDITIONAL
            }
            strategy = strategy_map.get(decomposed.execution_mode, ExecutionStrategy.SEQUENTIAL)

            plan = ExecutionPlan(
                steps=steps,
                strategy=strategy,
                intent=intent,
                estimated_time=decomposed.total_estimated_time,
                parallel_groups=decomposed.parallel_groups,
                metadata={
                    "is_compound": True,
                    "decomposition": decomposed.to_dict() if hasattr(decomposed, 'to_dict') else {},
                    "created_by": "PlanningAgent with QueryDecomposer"
                }
            )
        else:
            # 단순 질문: 기존 방식으로 계획 수립
            plan = await self.create_execution_plan(intent)

        # 4. 계획 검증 및 최적화
        is_valid, errors = await self.validate_dependencies(plan)
        if not is_valid:
            logger.warning(f"Plan validation errors: {errors}")

        plan = await self.optimize_plan(plan)

        logger.info(f"Comprehensive plan created: {self.get_plan_summary(plan)}")
        return plan

    async def create_execution_plan(
        self,
        intent: IntentResult,
        available_agents: Optional[List[str]] = None
    ) -> ExecutionPlan:
        """
        실행 계획 생성

        Args:
            intent: 의도 분석 결과
            available_agents: 사용 가능한 Agent 목록

        Returns:
            실행 계획
        """
        logger.info(f"Creating execution plan for intent: {intent.intent_type.value}")

        # IRRELEVANT 의도는 빈 계획 반환 (에이전트 실행하지 않음)
        if intent.intent_type == IntentType.IRRELEVANT:
            logger.info("Intent is IRRELEVANT, returning empty execution plan")
            return ExecutionPlan(
                steps=[],
                strategy=ExecutionStrategy.SEQUENTIAL,
                intent=intent,
                estimated_time=0.0,
                parallel_groups=[],
                metadata={"created_by": "PlanningAgent", "reason": "irrelevant_query"}
            )

        # UNCLEAR이고 confidence가 낮으면 빈 계획 반환
        if intent.intent_type == IntentType.UNCLEAR and intent.confidence < 0.3:
            logger.info(f"Intent is UNCLEAR with low confidence ({intent.confidence:.2f}), returning empty execution plan")
            return ExecutionPlan(
                steps=[],
                strategy=ExecutionStrategy.SEQUENTIAL,
                intent=intent,
                estimated_time=0.0,
                parallel_groups=[],
                metadata={"created_by": "PlanningAgent", "reason": "unclear_low_confidence"}
            )

        # 사용 가능한 Agent 확인
        if available_agents is None:
            available_agents = AgentRegistry.list_agents(enabled_only=True)
            # Fallback: AgentRegistry가 비어있으면 기본 팀 사용
            if not available_agents:
                available_agents = ["search_team", "analysis_team", "document_team"]
                logger.warning("AgentRegistry is empty, using default teams")

        # 추천 Agent 중 사용 가능한 것만 필터링
        logger.debug(f"Suggested agents: {intent.suggested_agents}")
        logger.debug(f"Available agents: {available_agents}")

        selected_agents = [
            agent for agent in intent.suggested_agents
            if agent in available_agents
        ]

        # Team 기반 아키텍처를 위한 폴백
        if not selected_agents:
            # Team 이름으로 시도
            if "search_team" in available_agents:
                selected_agents = ["search_team"]
            # 기존 agent 이름으로 폴백
            elif "search_agent" in available_agents:
                selected_agents = ["search_agent"]

        logger.info(f"Selected agents/teams for execution: {selected_agents}")

        # 실행 단계 생성
        steps = self._create_execution_steps(selected_agents, intent)

        # 전략 결정
        strategy = self._determine_strategy(intent, steps)

        # 병렬 그룹 생성
        parallel_groups = self._create_parallel_groups(steps) if strategy == ExecutionStrategy.PARALLEL else []

        return ExecutionPlan(
            steps=steps,
            strategy=strategy,
            intent=intent,
            estimated_time=self._estimate_execution_time(steps),
            parallel_groups=parallel_groups,
            metadata={"created_by": "PlanningAgent"}
        )

    def _create_execution_steps(
        self,
        selected_agents: List[str],
        intent: IntentResult
    ) -> List[ExecutionStep]:
        """실행 단계 생성"""
        steps = []

        for i, agent_name in enumerate(selected_agents):
            dependencies = []

            # Agent별 의존성 설정
            if agent_name == "analysis_agent" and "search_agent" in selected_agents:
                dependencies = ["search_agent"]
            elif agent_name == "review_agent" and "document_agent" in selected_agents:
                dependencies = ["document_agent"]

            step = ExecutionStep(
                agent_name=agent_name,
                priority=i,
                dependencies=dependencies,
                input_mapping=self._create_input_mapping(agent_name, intent),
                timeout=30 if agent_name != "analysis_agent" else 45,
                retry_count=2 if agent_name == "search_agent" else 1,
                optional=False
            )
            steps.append(step)

        return steps

    def _create_input_mapping(self, agent_name: str, intent: IntentResult) -> Dict[str, str]:
        """Agent별 입력 매핑 생성"""
        base_mapping = {
            "keywords": "intent.keywords",
            "entities": "intent.entities"
        }

        agent_specific = {
            "analysis_agent": {
                "input_data": "search_agent.collected_data",
                "analysis_type": "comprehensive"
            },
            "document_agent": {
                "document_type": intent.entities.get("document_type", "lease_contract"),
                "params": "intent.entities"
            },
            "review_agent": {
                "document": "document_agent.generated_document",
                "review_type": "comprehensive"
            }
        }

        mapping = base_mapping.copy()
        if agent_name in agent_specific:
            mapping.update(agent_specific[agent_name])

        return mapping

    def _determine_strategy(self, intent: IntentResult, steps: List[ExecutionStep]) -> ExecutionStrategy:
        """실행 전략 결정"""
        # 의존성이 있는 경우
        has_dependencies = any(step.dependencies for step in steps)
        if has_dependencies:
            return ExecutionStrategy.SEQUENTIAL

        # 병렬 처리: 여러 독립적인 데이터 소스 조회가 필요한 경우
        parallel_intents = [
            IntentType.COMPREHENSIVE,              # 종합분석 - 여러 관점에서 동시 분석
            IntentType.LOAN_COMPARISON,            # 대출비교 - 여러 은행 상품 동시 조회
            IntentType.PROPERTY_RECOMMENDATION,    # 맞춤추천 - 시세/인프라/법률 동시 분석
            IntentType.PROPERTY_INFRA_ANALYSIS,    # 매물인프라분석 - 지하철/마트/병원/학교 동시 조회
        ]
        if intent.intent_type in parallel_intents and len(steps) > 1:
            return ExecutionStrategy.PARALLEL

        # 파이프라인 처리: 순차적이지만 스트리밍 방식으로 처리 가능한 경우
        pipeline_intents = [
            IntentType.CONTRACT_CREATION,       # 계약서생성 - 생성 → 검토 파이프라인
            IntentType.ROI_CALCULATION,         # 투자수익률 - 데이터수집 → 계산 → 시뮬레이션
        ]
        agent_names = [step.agent_name for step in steps]
        if intent.intent_type in pipeline_intents:
            return ExecutionStrategy.PIPELINE
        # 레거시: document_agent + review_agent 조합도 파이프라인
        if "document_agent" in agent_names and "review_agent" in agent_names:
            return ExecutionStrategy.PIPELINE

        # 조건부 처리: 이전 결과에 따라 다음 단계가 달라지는 경우
        conditional_intents = [
            IntentType.PRICE_EVALUATION,        # 가격평가 - 시세 확인 후 추가 분석 필요 여부 판단
            IntentType.PROPERTY_SEARCH,         # 매물검색 - 검색 결과에 따라 추가 필터링 여부 결정
        ]
        if intent.intent_type in conditional_intents and len(steps) > 1:
            return ExecutionStrategy.CONDITIONAL

        # 순차 처리: 기본값 및 단순 조회
        # TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY, POLICY_INQUIRY 등
        return ExecutionStrategy.SEQUENTIAL

    def _create_parallel_groups(self, steps: List[ExecutionStep]) -> List[List[str]]:
        """병렬 실행 그룹 생성"""
        groups = []
        processed = set()

        for step in steps:
            if step.agent_name in processed:
                continue

            # 의존성이 없는 Agent들을 그룹화
            if not step.dependencies:
                group = [step.agent_name]
                for other in steps:
                    if (other.agent_name not in processed and
                        not other.dependencies and
                        other.agent_name != step.agent_name):
                        group.append(other.agent_name)
                        processed.add(other.agent_name)

                groups.append(group)
                processed.add(step.agent_name)

        # 의존성이 있는 Agent들은 별도 그룹
        for step in steps:
            if step.agent_name not in processed:
                groups.append([step.agent_name])

        return groups

    def _estimate_execution_time(self, steps: List[ExecutionStep]) -> float:
        """예상 실행 시간 계산"""
        if not steps:
            return 0.0

        total_time = 0.0
        for step in steps:
            # 병렬 실행 가능한 경우 최대 시간만 계산
            if not step.dependencies:
                total_time = max(total_time, step.timeout)
            else:
                total_time += step.timeout

        return total_time

    async def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        실행 계획 최적화

        Args:
            plan: 원본 실행 계획

        Returns:
            최적화된 실행 계획
        """
        logger.info("Optimizing execution plan")

        # 1. 불필요한 Agent 제거
        optimized_steps = self._remove_redundant_agents(plan.steps)

        # 2. 병렬화 가능성 재검토
        if len(optimized_steps) > 1:
            plan.strategy = self._determine_strategy(plan.intent, optimized_steps)
            if plan.strategy == ExecutionStrategy.PARALLEL:
                plan.parallel_groups = self._create_parallel_groups(optimized_steps)

        # 3. 타임아웃 조정
        for step in optimized_steps:
            if plan.intent.confidence < 0.5:
                step.timeout = int(step.timeout * 1.2)  # 불확실한 경우 시간 증가

        plan.steps = optimized_steps
        plan.estimated_time = self._estimate_execution_time(optimized_steps)

        return plan

    def _remove_redundant_agents(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """중복/불필요한 Agent 제거"""
        # 현재는 단순 구현 - 추후 고도화 가능
        return steps

    async def validate_dependencies(self, plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """
        의존성 검증

        Args:
            plan: 실행 계획

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        for step in plan.steps:
            # 의존성이 있는 Agent 확인
            for dep in step.dependencies:
                dep_exists = any(s.agent_name == dep for s in plan.steps)
                if not dep_exists:
                    errors.append(f"Agent '{step.agent_name}' depends on missing '{dep}'")

            # Agent가 Registry에 있는지 확인
            if not AgentRegistry.get_agent(step.agent_name):
                errors.append(f"Agent '{step.agent_name}' not found in registry")

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_plan_summary(self, plan: ExecutionPlan) -> str:
        """실행 계획 요약"""
        summary_parts = [
            f"Intent: {plan.intent.intent_type.value} (confidence: {plan.intent.confidence:.2f})",
            f"Strategy: {plan.strategy.value}",
            f"Agents: {', '.join(step.agent_name for step in plan.steps)}",
            f"Estimated time: {plan.estimated_time:.1f}s"
        ]

        if plan.parallel_groups:
            summary_parts.append(f"Parallel groups: {plan.parallel_groups}")

        return " | ".join(summary_parts)


# 사용 예시
if __name__ == "__main__":
    import asyncio

    async def test_planning_agent():
        planner = PlanningAgent()

        # 단순 질문 테스트
        simple_queries = [
            "전세금 5% 인상이 가능한가요?",
            "강남구 아파트 시세 알려주세요",
            "임대차계약서 작성해주세요",
        ]

        print("=== 단순 질문 테스트 ===")
        for query in simple_queries:
            print(f"\n질문: {query}")
            intent = await planner.analyze_intent(query)
            print(f"의도: {intent.intent_type.value} (신뢰도: {intent.confidence:.2f})")
            print(f"추천 Agent: {intent.suggested_agents}")

            # 실행 계획 생성
            plan = await planner.create_execution_plan(intent)
            print(f"계획 요약: {planner.get_plan_summary(plan)}")

        # Phase 1: 복합 질문 테스트
        complex_queries = [
            "강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘",
            "이 계약서 검토해서 위험한 부분 찾고 수정안 만들어줘",
            "서초동 전세가 확인하고 법적으로 문제없는지도 봐줘"
        ]

        print("\n\n=== 복합 질문 테스트 (Phase 1 Enhancement) ===")
        for query in complex_queries:
            print(f"\n복합 질문: {query}")
            plan = await planner.create_comprehensive_plan(query)
            print(f"전체 계획: {planner.get_plan_summary(plan)}")
            print(f"분해된 작업 수: {len(plan.steps)}")
            for step in plan.steps:
                print(f"  - {step.agent_name}: 우선순위 {step.priority}, 의존성 {step.dependencies}")

    asyncio.run(test_planning_agent())