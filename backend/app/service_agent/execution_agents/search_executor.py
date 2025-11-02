"""
Search Executor - 검색 실행 Agent
법률, 부동산, 대출 검색을 병렬/순차적으로 수행
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent 
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.separated_states import SearchTeamState, SearchKeywords, SharedState
from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import AgentAdapter
from app.service_agent.llm_manager import LLMService
from app.service_agent.foundation.decision_logger import DecisionLogger

logger = logging.getLogger(__name__)


class SearchExecutor:
    """
    검색 실행 Agent
    법률, 부동산, 대출 검색 작업을 실행
    """

    def __init__(self, llm_context=None, progress_callback=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
            progress_callback: 진행 상황 콜백 함수 (WebSocket 전송용)
        """
        self.llm_context = llm_context
        self.progress_callback = progress_callback

        # LLMService 초기화 (에러 발생 시 fallback)
        try:
            self.llm_service = LLMService(llm_context=llm_context)
            logger.info("✅ LLMService initialized successfully in SearchExecutor")
        except Exception as e:
            logger.error(f"❌ LLMService initialization failed: {e}", exc_info=True)
            self.llm_service = None

        self.team_name = "search"

        # Agent 초기화 (Registry에서 가져오기)
        self.available_agents = self._initialize_agents()

        # 검색 도구 초기화
        self.legal_search_tool = None
        self.market_data_tool = None
        self.real_estate_search_tool = None  # ✅ Phase 2 추가
        self.loan_data_tool = None

        # 공공데이터 API 도구 (NEW)
        self.transaction_price_tool = None
        self.building_registry_tool = None
        self.infrastructure_tool = None

        # 부동산 용어 검색 도구
        self.terminology_tool = None

        # Decision Logger 초기화
        try:
            self.decision_logger = DecisionLogger()
        except Exception as e:
            logger.warning(f"DecisionLogger initialization failed: {e}")
            self.decision_logger = None

        try:
            from app.service_agent.tools.legal_search_tool import LegalSearch
            self.legal_search_tool = LegalSearch()
            logger.info("LegalSearch initialized successfully")
        except Exception as e:
            logger.warning(f"LegalSearch initialization failed: {e}")

        try:
            from app.service_agent.tools.market_data_tool import MarketDataTool
            self.market_data_tool = MarketDataTool()
            logger.info("MarketDataTool initialized successfully")
        except Exception as e:
            logger.warning(f"MarketDataTool initialization failed: {e}")

        try:
            from app.service_agent.tools.loan_data_tool import LoanDataTool
            self.loan_data_tool = LoanDataTool()
            logger.info("LoanDataTool initialized successfully")
        except Exception as e:
            logger.warning(f"LoanDataTool initialization failed: {e}")

        try:
            from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool
            self.real_estate_search_tool = RealEstateSearchTool()
            logger.info("RealEstateSearchTool initialized successfully (PostgreSQL)")
        except Exception as e:
            logger.warning(f"RealEstateSearchTool initialization failed: {e}")

        # 공공데이터 API 도구 초기화 (NEW)
        try:
            from app.service_agent.tools import InfrastructureTool
            self.infrastructure_tool = InfrastructureTool()
            logger.info("InfrastructureTool initialized successfully")
        except Exception as e:
            logger.warning(f"InfrastructureTool initialization failed: {e}")

        try:
            from app.service_agent.tools import TransactionPriceTool
            self.transaction_price_tool = TransactionPriceTool()
            logger.info("TransactionPriceTool initialized successfully")
        except Exception as e:
            logger.warning(f"TransactionPriceTool initialization failed: {e}")

        try:
            from app.service_agent.tools import BuildingRegistryTool
            self.building_registry_tool = BuildingRegistryTool()
            logger.info("BuildingRegistryTool initialized successfully")
        except Exception as e:
            logger.warning(f"BuildingRegistryTool initialization failed: {e}")

        # 부동산 용어 검색 도구 초기화
        try:
            from app.service_agent.tools import RealEstateTerminologyTool
            self.terminology_tool = RealEstateTerminologyTool()
            logger.info("RealEstateTerminologyTool initialized successfully")
        except Exception as e:
            logger.warning(f"RealEstateTerminologyTool initialization failed: {e}")

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _initialize_agents(self) -> Dict[str, bool]:
        """사용 가능한 Agent 확인"""
        agent_types = ["search_agent"]  # 현재는 통합 SearchAgent 사용
        available = {}

        for agent_name in agent_types:
            available[agent_name] = agent_name in AgentRegistry.list_agents(enabled_only=True)

        logger.info(f"SearchTeam available agents: {available}")
        return available

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(SearchTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_search_node)
        workflow.add_node("route", self.route_search_node)
        workflow.add_node("search", self.execute_search_node)
        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START,"prepare")
        workflow.add_edge("prepare", "route")

        # 라우팅 후 검색 또는 종료
        workflow.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "search": "search",
                "skip": "finalize"
            }
        )

        workflow.add_edge("search", "aggregate")
        workflow.add_edge("aggregate", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("SearchTeam subgraph built successfully")

    def _route_decision(self, state: SearchTeamState) -> str:
        """검색 실행 여부 결정"""
        if not state.get("search_scope"):
            return "skip"
        return "search"

    async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 준비 노드
        키워드 추출 및 검색 범위 설정
        """
        logger.info("[SearchTeam] Preparing search")

        # 초기화
        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()
        state["search_progress"] = {}

        # 키워드가 없으면 쿼리에서 추출
        if not state.get("keywords"):
            query = state.get("shared_context", {}).get("query", "")
            state["keywords"] = self._extract_keywords(query)

        # 검색 범위가 없으면 키워드 기반으로 결정
        if not state.get("search_scope"):
            state["search_scope"] = self._determine_search_scope(state["keywords"])

        logger.info(f"[SearchTeam] Search scope: {state['search_scope']}")
        return state

    def _extract_keywords(self, query: str) -> SearchKeywords:
        """쿼리에서 키워드 추출 - LLM 사용 시 더 정확함"""
        # LLM이 있으면 LLM 기반 추출, 없으면 패턴 매칭
        if self.llm_service:
            try:
                return self._extract_keywords_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM keyword extraction failed, using fallback: {e}")

        # Fallback: 패턴 매칭 기반 키워드 추출
        return self._extract_keywords_with_patterns(query)

    def _extract_keywords_with_llm(self, query: str) -> SearchKeywords:
        """LLM을 사용한 키워드 추출 (LLMService 사용)"""
        try:
            # LLMService를 통한 키워드 추출
            result = self.llm_service.complete_json(
                prompt_name="keyword_extraction",
                variables={"query": query},
                temperature=0.1
            )

            # JSON 직렬화하여 로깅 (object object 출력 방지)
            import json
            logger.info(f"LLM Keyword Extraction: {json.dumps(result, ensure_ascii=False)}")

            return SearchKeywords(
                legal=result.get("legal", []),
                real_estate=result.get("real_estate", []),
                loan=result.get("loan", []),
                general=result.get("general", [])
            )
        except Exception as e:
            logger.error(f"LLM keyword extraction failed: {e}")
            raise

    def _extract_keywords_with_patterns(self, query: str) -> SearchKeywords:
        """패턴 매칭 기반 키워드 추출 (Fallback)"""
        legal_keywords = []
        real_estate_keywords = []
        loan_keywords = []
        general_keywords = []

        # 법률 관련 키워드
        legal_terms = ["법", "전세", "임대", "계약", "보증금", "권리", "의무", "갱신", "임차인", "임대인"]
        for term in legal_terms:
            if term in query:
                legal_keywords.append(term)

        # 부동산 관련 키워드
        estate_terms = ["아파트", "빌라", "오피스텔", "시세", "매매", "가격", "평수", "지역", "강남", "강북", "서초", "송파"]
        for term in estate_terms:
            if term in query:
                real_estate_keywords.append(term)

        # 대출 관련 키워드
        loan_terms = ["대출", "금리", "한도", "LTV", "DTI", "DSR", "담보", "신용"]
        for term in loan_terms:
            if term in query:
                loan_keywords.append(term)

        # 일반 키워드 (숫자, 퍼센트 등)
        import re
        numbers = re.findall(r'\d+[%억만원평]?', query)
        general_keywords.extend(numbers)

        return SearchKeywords(
            legal=legal_keywords,
            real_estate=real_estate_keywords,
            loan=loan_keywords,
            general=general_keywords
        )

    def _get_available_tools(self) -> Dict[str, Any]:
        """
        현재 SearchExecutor에서 사용 가능한 tool 정보를 동적으로 수집
        하드코딩 없이 실제 초기화된 tool만 반환
        """
        tools = {}

        if self.legal_search_tool:
            tools["legal_search"] = {
                "name": "legal_search",
                "description": "법률 정보 검색 (전세법, 임대차보호법, 부동산 관련 법규)",
                "capabilities": [
                    "전세금 인상률 조회",
                    "임차인 권리 확인",
                    "계약갱신 조건",
                    "임대차 관련 법률"
                ],
                "available": True
            }

        if self.market_data_tool:
            tools["market_data"] = {
                "name": "market_data",
                "description": "부동산 시세 조회 (매매가, 전세가, 월세)",
                "capabilities": [
                    "지역별 시세 조회",
                    "실거래가 정보",
                    "평균 가격 조회",
                    "시세 동향"
                ],
                "available": True
            }

        if self.real_estate_search_tool:
            tools["real_estate_search"] = {
                "name": "real_estate_search",
                "description": "개별 부동산 매물 검색 (아파트, 오피스텔 등)",
                "capabilities": [
                    "지역별 매물 조회",
                    "가격대별 필터링",
                    "면적별 검색",
                    "준공년도 검색",
                    "주변 시설 정보",
                    "실거래가 내역"
                ],
                "available": True
            }

        if self.loan_data_tool:
            tools["loan_data"] = {
                "name": "loan_data",
                "description": "대출 상품 정보 검색 (금리, 한도, 조건)",
                "capabilities": [
                    "전세자금대출",
                    "주택담보대출",
                    "금리 정보",
                    "대출 한도"
                ],
                "available": True
            }

        # 공공데이터 API 도구 (NEW)
        if self.infrastructure_tool:
            tools["infrastructure"] = {
                "name": "infrastructure",
                "description": "부동산 주변 인프라 정보 검색 (지하철, 학교, 편의시설)",
                "capabilities": [
                    "주변 지하철역 검색",
                    "초/중/고등학교 검색",
                    "대형마트 검색 ",
                    "종합 인프라 정보",
                    "거리 및 도보시간 제공"
                ],
                "available": True
            }

        if self.transaction_price_tool:
            tools["transaction_price"] = {
                "name": "transaction_price",
                "description": "국토부 실거래가 정보 (아파트, 오피스텔, 연립, 단독)",
                "capabilities": [
                    "아파트 매매/전월세 실거래가",
                    "오피스텔 실거래가",
                    "연립/다세대 실거래가",
                    "단독/다가구 실거래가",
                    "기간별 실거래가 조회"
                ],
                "available": True
            }

        if self.building_registry_tool:
            tools["building_registry"] = {
                "name": "building_registry",
                "description": "건축물대장 정보 (건축물 상세 스펙) - 주소 기반 검색 지원",
                "capabilities": [
                    "주소로 건축물 검색 (예: 서울시 강남구 역삼동 123-45)",
                    "건축물 면적 정보 (연면적)",
                    "층수 정보 (지상/지하)",
                    "준공년도",
                    "건물 구조 및 용도",
                    "사용승인일/허가일"
                ],
                "available": True
            }

        if self.terminology_tool:
            tools["realestate_terminology"] = {
                "name": "realestate_terminology",
                "description": "부동산 용어 정의 검색 (용어의 의미와 설명)",
                "capabilities": [
                    "부동산 용어 정의 (예: DSR, LTV, DTI)",
                    "대출 관련 용어 설명",
                    "매매/임대차 용어 검색",
                    "법률 용어 의미 조회",
                    "용어별 카테고리 정보"
                ],
                "available": True
            }

        return tools

    async def _select_tools_with_llm(
        self,
        query: str,
        keywords: SearchKeywords = None
    ) -> Dict[str, Any]:
        """
        LLM을 사용한 tool 선택 (수정 - 키워드 제거)

        Args:
            query: 사용자 쿼리 (키워드 없이 원본만)
            keywords: 하위 호환성을 위해 유지 (사용 안함)

        Returns:
            {
                "selected_tools": ["legal_search", "market_data", "loan_data"],
                "reasoning": "...",
                "confidence": 0.9,
                "decision_id": 123  # 로깅 ID
            }
        """
        if not self.llm_service:
            logger.warning("LLM service not available, using fallback")
            return self._select_tools_with_fallback(keywords=keywords, query=query)

        try:
            # 동적으로 사용 가능한 tool 정보 수집
            available_tools = self._get_available_tools()

            logger.info(f"[Tool Selection] Query: {query}")
            logger.info(f"[Tool Selection] Available tools: {list(available_tools.keys())}")

            result = await self.llm_service.complete_json_async(
                prompt_name="tool_selection_search",  # search 전용 prompt
                variables={
                    "query": query,  # 키워드 없이 원본 query만
                    "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
                },
                temperature=0.1
            )

            selected_tools = result.get("selected_tools", [])
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 0.0)

            logger.info(f"[Tool Selection] LLM Response:")
            logger.info(f"  - Selected: {selected_tools}")
            logger.info(f"  - Reasoning: {reasoning}")
            logger.info(f"  - Confidence: {confidence}")

            # ✅ 추가: 유효한 도구만 필터링 (LLM이 잘못된 도구 이름을 반환할 수 있음)
            valid_tools = [tool for tool in selected_tools if tool in available_tools]
            if len(valid_tools) != len(selected_tools):
                invalid_tools = [tool for tool in selected_tools if tool not in available_tools]
                logger.warning(f"[Tool Selection] Invalid tools filtered out: {invalid_tools}")
                logger.warning(f"[Tool Selection] Valid tools: {valid_tools}")
                selected_tools = valid_tools

            # ✅ 추가: 도구가 하나도 선택되지 않은 경우 fallback
            if not selected_tools:
                logger.error(f"[Tool Selection] No valid tools selected by LLM, using fallback")
                return self._select_tools_with_fallback(keywords=keywords, query=query)

            # Decision Logger에 기록
            decision_id = None
            if self.decision_logger:
                try:
                    decision_id = self.decision_logger.log_tool_decision(
                        agent_type="search",
                        query=query,
                        available_tools=available_tools,
                        selected_tools=selected_tools,
                        reasoning=reasoning,
                        confidence=confidence
                    )
                    logger.info(f"[Tool Selection] Decision logged with ID: {decision_id}")
                except Exception as e:
                    logger.warning(f"Failed to log tool decision: {e}")

            return {
                "selected_tools": selected_tools,
                "reasoning": reasoning,
                "confidence": confidence,
                "decision_id": decision_id
            }

        except Exception as e:
            logger.error(f"[Tool Selection] LLM tool selection failed: {e}", exc_info=True)
            return self._select_tools_with_fallback(keywords=keywords, query=query)

    def _select_tools_with_fallback(self, keywords: SearchKeywords = None, query: str = "") -> Dict[str, Any]:
        """
        규칙 기반 fallback tool 선택
        LLM 실패 시 사용 (안전망)

        ✅ 개선: 모든 도구 대신 질문 패턴 기반 최소 도구 세트 사용
        """
        available_tools = self._get_available_tools()

        # ✅ 개선: 키워드 기반 스마트 fallback
        query_lower = query.lower() if query else ""
        selected_tools = []

        # 법률 키워드
        if any(kw in query_lower for kw in ["법", "전세", "임대", "계약", "보증금", "권리", "의무", "갱신"]):
            if "legal_search" in available_tools:
                selected_tools.append("legal_search")

        # 시세 키워드
        if any(kw in query_lower for kw in ["시세", "가격", "평균", "비교", "얼마"]):
            if "market_data" in available_tools:
                selected_tools.append("market_data")

        # 매물 검색 키워드
        if any(kw in query_lower for kw in ["매물", "찾", "검색", "원룸", "아파트", "오피스텔", "빌라"]):
            if "real_estate_search" in available_tools:
                selected_tools.append("real_estate_search")

        # 대출 키워드
        if any(kw in query_lower for kw in ["대출", "금리", "ltv", "dti", "dsr", "한도"]):
            if "loan_data" in available_tools:
                selected_tools.append("loan_data")

        # 용어 설명 키워드
        if any(kw in query_lower for kw in ["뭐야", "무엇", "의미", "설명", "정의", "란"]):
            if "realestate_terminology" in available_tools:
                selected_tools.append("realestate_terminology")

        # 인프라 키워드
        if any(kw in query_lower for kw in ["지하철", "학교", "마트", "병원", "인프라", "주변", "근처"]):
            if "infrastructure" in available_tools:
                selected_tools.append("infrastructure")

        # 건축물대장 키워드
        if any(kw in query_lower for kw in ["건축물", "대장", "준공", "면적", "층"]):
            if "building_registry" in available_tools:
                selected_tools.append("building_registry")

        # 도구가 하나도 선택되지 않았으면 기본 도구 사용
        if not selected_tools:
            # 기본: legal_search (가장 범용적)
            if "legal_search" in available_tools:
                selected_tools.append("legal_search")
            # 또는 모든 도구 사용 (최후의 수단)
            if not selected_tools:
                selected_tools = list(available_tools.keys())
                logger.warning("[Tool Selection] No keyword match, using all available tools")

        reasoning = f"Fallback: keyword-based selection from query: '{query[:50]}...'"
        confidence = 0.5  # 0.3 → 0.5 (키워드 기반이므로 약간 높임)

        logger.info(f"[Tool Selection] Fallback selected: {selected_tools}")
        logger.info(f"[Tool Selection] Reasoning: {reasoning}")

        # Decision Logger에 기록 (fallback도 기록)
        decision_id = None
        if self.decision_logger and query:
            try:
                decision_id = self.decision_logger.log_tool_decision(
                    agent_type="search",
                    query=query,
                    available_tools=available_tools,
                    selected_tools=selected_tools,
                    reasoning=reasoning,
                    confidence=confidence
                )
            except Exception as e:
                logger.warning(f"Failed to log fallback tool decision: {e}")

        return {
            "selected_tools": selected_tools,
            "reasoning": reasoning,
            "confidence": confidence,
            "decision_id": decision_id
        }

    def _determine_search_scope(self, keywords: SearchKeywords) -> List[str]:
        """
        키워드 기반 검색 범위 결정 (Deprecated - use _select_tools_with_llm)
        하위 호환성을 위해 유지
        """
        scope = []

        if keywords.get("legal"):
            scope.append("legal")
        if keywords.get("real_estate"):
            scope.append("real_estate")
        if keywords.get("loan"):
            scope.append("loan")

        # 아무것도 없으면 법률 검색을 기본으로
        if not scope:
            scope = ["legal"]

        return scope

    async def route_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 라우팅 노드
        병렬/순차 실행 결정
        """
        logger.info("[SearchTeam] Routing search")

        # 검색할 Agent 확인
        search_scope = state.get("search_scope", [])

        if len(search_scope) > 1:
            state["execution_strategy"] = "parallel"
        else:
            state["execution_strategy"] = "sequential"

        return state

    async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 실행 노드
        실제 검색 Agent 호출 + 하이브리드 법률 검색
        """
        logger.info("[SearchTeam] Executing searches")

        import time
        start_time = time.time()

        search_scope = state.get("search_scope", [])
        keywords = state.get("keywords", {})
        shared_context = state.get("shared_context", {})
        query = shared_context.get("user_query", "") or shared_context.get("query", "")

        # LLM 기반 도구 선택
        tool_selection = await self._select_tools_with_llm(query, keywords)
        selected_tools = tool_selection.get("selected_tools", [])
        decision_id = tool_selection.get("decision_id")

        # 도구 선택 정보를 state에 저장 (디버깅용)
        state["selected_tools"] = selected_tools
        state["tool_selection_reasoning"] = tool_selection.get("reasoning", "")
        state["tool_selection_confidence"] = tool_selection.get("confidence", 0.0)

        logger.info(
            f"[SearchTeam] LLM selected tools: {selected_tools}, "
            f"confidence: {tool_selection.get('confidence')}"
        )

        # 실행 결과를 추적
        execution_results = {}
        tool_name_map = {
            "legal_search": "legal",
            "market_data": "real_estate",
            "loan_data": "loan"
        }

        # === 1. 법률 검색 (우선 실행) ===
        if "legal_search" in selected_tools and self.legal_search_tool:
            try:
                logger.info("[SearchTeam] Executing legal search")

                # LLM 기반 파라미터 추출
                search_params = await self._extract_parameters_with_llm(query, "legal_search")

                # 기본값 설정
                if "limit" not in search_params:
                    search_params["limit"] = 10

                # 임차인 보호 조항 필터 (추가)
                if any(term in query for term in ["임차인", "전세", "임대", "보증금"]):
                    search_params["is_tenant_protection"] = True

                logger.info(f"[SearchTeam] Legal search params: {search_params}")

                # 법률 검색 실행
                result = await self.legal_search_tool.search(query, search_params)

                # 결과 파싱
                if result.get("status") == "success":
                    legal_data = result.get("data", [])

                    # 결과 포맷 변환
                    state["legal_results"] = [
                        {
                            "law_title": item.get("law_title", ""),
                            "article_number": item.get("article_number", ""),
                            "article_title": item.get("article_title", ""),
                            "content": item.get("content", ""),
                            "relevance_score": 1.0 - item.get("distance", 0.0),
                            "chapter": item.get("chapter"),
                            "section": item.get("section"),
                            "source": "legal_db"
                        }
                        for item in legal_data
                    ]

                    state["search_progress"]["legal_search"] = "completed"
                    logger.info(f"[SearchTeam] Legal search completed: {len(legal_data)} results")
                    execution_results["legal_search"] = {
                        "status": "success",
                        "result_count": len(legal_data)
                    }
                else:
                    state["search_progress"]["legal_search"] = "failed"
                    logger.warning(f"Legal search returned status: {result.get('status')}")
                    execution_results["legal_search"] = {
                        "status": "failed",
                        "error": result.get('status')
                    }

            except Exception as e:
                logger.error(f"Legal search failed: {e}")
                state["search_progress"]["legal_search"] = "failed"
                execution_results["legal_search"] = {
                    "status": "error",
                    "error": str(e)
                }
                # 실패해도 계속 진행

        # === 2. 부동산 시세 검색 ===
        if "market_data" in selected_tools and self.market_data_tool:
            try:
                logger.info("[SearchTeam] Executing real estate search")

                # 부동산 검색 실행
                result = await self.market_data_tool.search(query, {})

                if result.get("status") == "success":
                    market_data = result.get("data", [])

                    # 결과 포맷 변환
                    state["real_estate_results"] = market_data
                    state["search_progress"]["real_estate_search"] = "completed"
                    logger.info(f"[SearchTeam] Real estate search completed: {len(market_data)} results")
                    execution_results["market_data"] = {
                        "status": "success",
                        "result_count": len(market_data)
                    }
                else:
                    state["search_progress"]["real_estate_search"] = "failed"
                    execution_results["market_data"] = {
                        "status": "failed",
                        "error": result.get('status')
                    }

            except Exception as e:
                logger.error(f"Real estate search failed: {e}")
                state["search_progress"]["real_estate_search"] = "failed"
                execution_results["market_data"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 3. 대출 상품 검색 ===
        if "loan_data" in selected_tools and self.loan_data_tool:
            try:
                logger.info("[SearchTeam] Executing loan search")

                # 대출 검색 실행
                result = await self.loan_data_tool.search(query, {})

                if result.get("status") == "success":
                    loan_data = result.get("data", [])

                    # 결과 포맷 변환
                    state["loan_results"] = loan_data
                    state["search_progress"]["loan_search"] = "completed"
                    logger.info(f"[SearchTeam] Loan search completed: {len(loan_data)} results")
                    execution_results["loan_data"] = {
                        "status": "success",
                        "result_count": len(loan_data)
                    }
                else:
                    state["search_progress"]["loan_search"] = "failed"
                    execution_results["loan_data"] = {
                        "status": "failed",
                        "error": result.get('status')
                    }

            except Exception as e:
                logger.error(f"Loan search failed: {e}")
                state["search_progress"]["loan_search"] = "failed"
                execution_results["loan_data"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 3-0. 부동산 용어 검색 ===
        if "realestate_terminology" in selected_tools and self.terminology_tool:
            try:
                logger.info("[SearchTeam] Executing real estate terminology search")

                # LLM 기반 파라미터 추출
                search_params = await self._extract_parameters_with_llm(query, "realestate_terminology")
                top_k = search_params.get("top_k", 5)  # 기본값: 5

                logger.info(f"[SearchTeam] Terminology search params: top_k={top_k}")

                # 용어 검색 실행
                result = self.terminology_tool.search_terminology(query, top_k=top_k)

                logger.info(f"[SearchTeam] Terminology tool returned: success={result.get('success')}, "
                           f"total_found={result.get('total_found', 0)}, results={len(result.get('results', []))}")

                if result.get("success"):
                    terminology_data = result.get("results", [])

                    # 결과 저장
                    state["terminology_results"] = terminology_data
                    state["search_progress"]["terminology_search"] = "completed"
                    logger.info(f"[SearchTeam] Terminology search completed: {len(terminology_data)} results")

                    # 결과가 비어있어도 경고 표시
                    if len(terminology_data) == 0:
                        logger.warning(f"[SearchTeam] Terminology search returned 0 results for query: '{query}'")
                    execution_results["realestate_terminology"] = {
                        "status": "success",
                        "result_count": len(terminology_data)
                    }
                else:
                    state["search_progress"]["terminology_search"] = "failed"
                    execution_results["realestate_terminology"] = {
                        "status": "failed",
                        "error": result.get("error", "Unknown error")
                    }

            except Exception as e:
                logger.error(f"Terminology search failed: {e}")
                state["search_progress"]["terminology_search"] = "failed"
                execution_results["realestate_terminology"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 3-1. 개별 부동산 매물 검색 (Phase 2) ===
        if "real_estate_search" in selected_tools and self.real_estate_search_tool:
            try:
                logger.info("[SearchTeam] Executing individual real estate property search")

                # LLM 기반 파라미터 추출
                search_params = await self._extract_parameters_with_llm(query, "real_estate_search")
                logger.info(f"[Parameter Extraction] Extracted params: {search_params}")

                # 검색 실행
                result = await self.real_estate_search_tool.search(query, search_params)

                if result.get("status") == "success":
                    property_data = result.get("data", [])

                    # 결과를 별도 키에 저장 (기존 real_estate_results와 구분)
                    state["property_search_results"] = property_data
                    state["search_progress"]["property_search"] = "completed"
                    logger.info(f"[SearchTeam] Property search completed: {len(property_data)} results")
                    execution_results["real_estate_search"] = {
                        "status": "success",
                        "result_count": len(property_data)
                    }
                else:
                    state["search_progress"]["property_search"] = "failed"
                    execution_results["real_estate_search"] = {
                        "status": "failed",
                        "error": result.get('status')
                    }

            except Exception as e:
                logger.error(f"Property search failed: {e}")
                state["search_progress"]["property_search"] = "failed"
                execution_results["real_estate_search"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 4. 주변 인프라 검색 (NEW) ===
        if "infrastructure" in selected_tools and self.infrastructure_tool:
            try:
                logger.info("[SearchTeam] Executing infrastructure search")

                # 쿼리에서 부동산 이름 추출 (개선된 로직)
                property_name = None
                import re

                # Pattern 1: "XXX 주변/근처/인근" 형태 (공백 포함하여 여러 단어 매칭)
                match = re.search(r'([가-힣A-Za-z0-9\s]+?)\s*(주변|근처|인근)', query)
                if match:
                    property_name = match.group(1).strip()
                    logger.info(f"[Pattern 1] Extracted property name: '{property_name}'")

                # Pattern 2: "XXX 아파트" 형태 (주변/근처 없어도 매칭)
                if not property_name:
                    match = re.search(r'([가-힣A-Za-z0-9\s]+?)\s*(아파트|빌라|오피스텔|맨션|타운)', query)
                    if match:
                        property_name = (match.group(1) + ' ' + match.group(2)).strip()
                        logger.info(f"[Pattern 2] Extracted property name: '{property_name}'")

                # Pattern 3: 첫 번째 명사구 추출 (최후의 수단)
                if not property_name:
                    # "지하철", "대형마트" 같은 키워드 전까지만 추출
                    match = re.search(r'^([가-힣A-Za-z0-9\s]+?)\s*(지하철|마트|학교|병원|인프라)', query)
                    if match:
                        property_name = match.group(1).strip()
                        logger.info(f"[Pattern 3] Extracted property name: '{property_name}'")

                if property_name:
                    # 불필요한 단어 제거
                    property_name = re.sub(r'\s+(에|에서|의|을|를|은|는|이|가|도|만)\s*$', '', property_name)
                    logger.info(f"[Final] Property name after cleanup: '{property_name}'")

                # 부동산 좌표 조회
                latitude = None
                longitude = None
                coordinate_source = None

                # Step 1: PostgreSQL에서 좌표 조회 시도
                if property_name and self.real_estate_search_tool:
                    property_result = await self.real_estate_search_tool.search(
                        query=property_name,
                        params={
                            "property_name": property_name,  # 이름으로 검색
                            "limit": 1
                        }
                    )

                    if property_result.get("status") == "success" and property_result.get("data"):
                        first_property = property_result["data"][0]
                        latitude = first_property.get("latitude")
                        longitude = first_property.get("longitude")

                        if latitude and longitude:
                            logger.info(f"✅ Found coordinates from DB for {property_name}: ({latitude}, {longitude})")
                            coordinate_source = "database"

                # Step 2: DB에 좌표 없으면 Geocoding API로 검색
                if not latitude or not longitude:
                    if property_name:
                        logger.info(f"⚠️ No coordinates in DB, trying geocoding for: {property_name}")
                        geocode_result = self.infrastructure_tool.geocode_address(property_name)

                        if geocode_result:
                            latitude = geocode_result.get("latitude")
                            longitude = geocode_result.get("longitude")
                            logger.info(f"✅ Found coordinates via geocoding for {property_name}: ({latitude}, {longitude})")
                            coordinate_source = "geocoding"
                        else:
                            logger.warning(f"❌ Geocoding also failed for: {property_name}")
                    else:
                        logger.warning("❌ No property name extracted from query")

                # 인프라 검색 실행
                if latitude and longitude:
                    infrastructure_result = self.infrastructure_tool.get_comprehensive_infrastructure(
                        latitude=float(latitude),
                        longitude=float(longitude),
                        radius=1000
                    )

                    if infrastructure_result.get("status") == "success":
                        infra_data = infrastructure_result.get("infrastructure", {})
                        state["infrastructure_results"] = infra_data
                        state["search_progress"]["infrastructure"] = "completed"

                        logger.info(f"[SearchTeam] Saved infrastructure_results to state: {len(str(infra_data))} bytes")

                        execution_results["infrastructure"] = {
                            "status": "success",
                            "facility_count": infrastructure_result.get("total_count", 0),
                            "property_name": property_name,
                            "coordinate_source": coordinate_source  # "database" or "geocoding"
                        }
                    else:
                        state["search_progress"]["infrastructure"] = "failed"
                        execution_results["infrastructure"] = {
                            "status": "error",
                            "error": infrastructure_result.get("error", "Unknown error")
                        }
                else:
                    state["search_progress"]["infrastructure"] = "skipped"
                    execution_results["infrastructure"] = {
                        "status": "skipped",
                        "reason": f"Could not find coordinates for '{property_name or query}'"
                    }

            except Exception as e:
                logger.error(f"[SearchTeam] Infrastructure search failed: {e}")
                state["search_progress"]["infrastructure"] = "failed"
                execution_results["infrastructure"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 5. 건축물 대장 검색 (NEW) ===
        if "building_registry" in selected_tools and self.building_registry_tool:
            try:
                logger.info("[SearchTeam] Executing building registry search")

                # LLM 기반 파라미터 추출
                search_params = await self._extract_parameters_with_llm(query, "building_registry")

                address = search_params.get("address")
                property_name = search_params.get("property_name")

                logger.info(f"[SearchTeam] Extracted params - address: {address}, property_name: {property_name}")

                # 주소가 없으면 건물명으로 주소 찾기
                if not address and property_name:
                    # real_estate_search_tool을 사용해서 건물의 주소 찾기
                    if self.real_estate_search_tool:
                        logger.info(f"[SearchTeam] Finding address for property: {property_name}")
                        prop_result = await self.real_estate_search_tool.search(
                            query=property_name,
                            search_params={"property_name": property_name, "limit": 1}
                        )

                        if prop_result.get("status") == "success" and prop_result.get("data"):
                            address = prop_result["data"][0].get("address")
                            logger.info(f"[SearchTeam] Found address for {property_name}: {address}")

                if address:
                    logger.info(f"[SearchTeam] Searching building registry for address: {address}")

                    # 건축물 대장 검색 실행
                    result = self.building_registry_tool.search_by_address(
                        address=address,
                        info_type=search_params.get("info_type", "basic"),
                        limit=search_params.get("limit", 5)
                    )

                    if result.get("status") == "success":
                        building_data = result.get("results", [])

                        # 결과가 있는 경우
                        if building_data:
                            state["building_registry_results"] = building_data
                            state["search_progress"]["building_registry"] = "completed"
                            logger.info(f"[SearchTeam] Building registry search completed: {len(building_data)} results")
                            execution_results["building_registry"] = {
                                "status": "success",
                                "result_count": len(building_data),
                                "address": address
                            }
                        else:
                            # API는 성공했지만 결과가 0개인 경우 (유효하지 않은 주소)
                            error_message = (
                                f"'{address}'에 대한 건축물 정보를 찾을 수 없습니다.\n"
                                "건축물 대장 조회를 위해서는 정확한 지번 주소가 필요합니다.\n"
                                "예시: '서울시 강남구 역삼동 123-45', '서초구 방배동 907'"
                            )

                            if property_name and property_name != address:
                                error_message += f"\n\n'{property_name}' 건물의 정확한 지번 주소를 찾을 수 없습니다."

                            state["search_progress"]["building_registry"] = "failed"
                            state["building_registry_results"] = [{
                                "error": True,
                                "message": error_message,
                                "suggestion": "정확한 지번 주소를 함께 입력해주세요.",
                                "example": "예: 서초구 방배동 907"
                            }]

                            execution_results["building_registry"] = {
                                "status": "failed",
                                "error": error_message,
                                "reason": "No results found for address"
                            }
                            logger.warning(f"[SearchTeam] {error_message}")
                    else:
                        # API 호출 자체가 실패한 경우
                        api_error = result.get("error", "Unknown error")
                        error_message = (
                            f"건축물 대장 조회 중 오류가 발생했습니다.\n"
                            f"오류 내용: {api_error}\n\n"
                            "정확한 지번 주소 형식으로 다시 시도해주세요.\n"
                            "예시: '서초구 방배동 907'"
                        )

                        state["search_progress"]["building_registry"] = "failed"
                        state["building_registry_results"] = [{
                            "error": True,
                            "message": error_message,
                            "api_error": api_error,
                            "suggestion": "주소 형식을 확인하고 다시 시도해주세요.",
                            "example": "예: 서초구 방배동 907"
                        }]

                        execution_results["building_registry"] = {
                            "status": "failed",
                            "error": api_error
                        }
                        logger.error(f"[SearchTeam] Building registry API error: {api_error}")
                else:
                    # 주소를 찾지 못한 경우 - 사용자에게 안내 메시지
                    error_message = (
                        "건축물 대장 조회를 위해서는 정확한 주소(지번 또는 도로명)가 필요합니다.\n"
                        f"예시: '서울시 강남구 역삼동 123-45', '서초구 방배동 907'\n"
                    )

                    if property_name:
                        error_message += f"\n'{property_name}' 건물의 정확한 지번 주소를 찾을 수 없습니다. 지번 주소를 함께 입력해주세요."

                    state["search_progress"]["building_registry"] = "failed"

                    # 결과 배열에 에러 메시지를 포함 (사용자에게 전달하기 위해)
                    state["building_registry_results"] = [{
                        "error": True,
                        "message": error_message,
                        "suggestion": "정확한 지번 주소를 함께 입력해주세요.",
                        "example": "예: 서초구 방배동 907"
                    }]

                    execution_results["building_registry"] = {
                        "status": "failed",
                        "error": error_message,
                        "reason": "No valid address found"
                    }

                    logger.warning(f"[SearchTeam] {error_message}")

            except Exception as e:
                logger.error(f"[SearchTeam] Building registry search failed: {e}")
                state["search_progress"]["building_registry"] = "failed"
                execution_results["building_registry"] = {
                    "status": "error",
                    "error": str(e)
                }

        # === 6. SearchAgent 실행 (추가 검색 필요 시) ===
        # 법률/부동산/대출 검색이 이미 완료되었으므로 scope에서 제외
        remaining_scope = [s for s in search_scope if s not in ["legal", "real_estate", "loan"]]

        if remaining_scope and self.available_agents.get("search_agent"):
            try:
                # SearchAgent 입력 준비
                search_input = {
                    "query": query,
                    "original_query": shared_context.get("original_query", query),
                    "chat_session_id": shared_context.get("session_id", ""),
                    "collection_keywords": self._flatten_keywords(keywords),
                    "search_scope": remaining_scope,
                    "shared_context": {},
                    "todos": [],
                    "todo_counter": 0
                }

                result = await AgentAdapter.execute_agent_dynamic(
                    "search_agent",
                    search_input,
                    self.llm_context
                )

                # 결과 파싱
                if result.get("status") in ["completed", "success"]:
                    collected_data = result.get("collected_data", {})

                    # 부동산 검색 결과
                    if "real_estate_search" in collected_data:
                        state["real_estate_results"] = collected_data["real_estate_search"]
                        state["search_progress"]["real_estate_search"] = "completed"

                    # 대출 검색 결과
                    if "loan_search" in collected_data:
                        state["loan_results"] = collected_data["loan_search"]
                        state["search_progress"]["loan_search"] = "completed"

                    state["search_progress"]["search_agent"] = "completed"
                else:
                    state["search_progress"]["search_agent"] = "failed"
                    state["error"] = result.get("error", "Search failed")

            except Exception as e:
                logger.error(f"Search execution failed: {e}")
                state["search_progress"]["search_agent"] = "failed"
                state["error"] = str(e)

        # 실행 시간 계산 및 결과 로깅
        total_execution_time_ms = int((time.time() - start_time) * 1000)

        if decision_id and self.decision_logger:
            try:
                # 전체 성공 여부 판단
                success = all(
                    r.get("status") == "success"
                    for r in execution_results.values()
                )

                self.decision_logger.update_tool_execution_results(
                    decision_id=decision_id,
                    execution_results=execution_results,
                    total_execution_time_ms=total_execution_time_ms,
                    success=success
                )

                logger.info(
                    f"[SearchTeam] Logged execution results: "
                    f"decision_id={decision_id}, success={success}, "
                    f"time={total_execution_time_ms}ms"
                )
            except Exception as e:
                logger.warning(f"Failed to log execution results: {e}")

        return state

    def _flatten_keywords(self, keywords: SearchKeywords) -> List[str]:
        """키워드 평탄화"""
        all_keywords = []
        if isinstance(keywords, dict):
            all_keywords.extend(keywords.get("legal", []))
            all_keywords.extend(keywords.get("real_estate", []))
            all_keywords.extend(keywords.get("loan", []))
            all_keywords.extend(keywords.get("general", []))
        return list(set(all_keywords))

    async def _extract_parameters_with_llm(self, query: str, tool_name: str) -> Dict[str, Any]:
        """
        LLM을 사용하여 쿼리에서 도구별 파라미터 추출

        Args:
            query: 사용자 쿼리
            tool_name: 도구 이름 (real_estate_search, infrastructure, etc.)

        Returns:
            추출된 파라미터 딕셔너리
        """
        if not self.llm_service:
            logger.warning("LLM service not available, using fallback parameter extraction")
            return self._extract_parameters_with_fallback(query, tool_name)

        try:
            logger.info(f"[Parameter Extraction] Extracting parameters for tool: {tool_name}")

            # LLM을 사용한 파라미터 추출
            result = await self.llm_service.complete_json_async(
                prompt_name="parameter_extraction",
                variables={"query": query},
                temperature=0.1
            )

            # 결과 검증
            if result.get("tool") == tool_name or tool_name in result.get("tool", ""):
                parameters = result.get("parameters", {})
                reasoning = result.get("reasoning", "")

                logger.info(f"[Parameter Extraction] Success:")
                logger.info(f"  - Tool: {result.get('tool')}")
                logger.info(f"  - Parameters: {parameters}")
                logger.info(f"  - Reasoning: {reasoning}")

                return parameters
            else:
                logger.warning(
                    f"[Parameter Extraction] Tool mismatch: "
                    f"expected {tool_name}, got {result.get('tool')}"
                )
                # 도구는 다르지만 파라미터는 사용 가능하면 반환
                return result.get("parameters", {})

        except Exception as e:
            logger.error(f"[Parameter Extraction] LLM extraction failed: {e}")
            return self._extract_parameters_with_fallback(query, tool_name)

    def _extract_parameters_with_fallback(self, query: str, tool_name: str) -> Dict[str, Any]:
        """
        Fallback: 정규식 기반 파라미터 추출
        LLM 실패 시 사용
        """
        import re
        search_params = {}

        logger.info(f"[Parameter Extraction] Using fallback for tool: {tool_name}")

        if tool_name == "real_estate_search":
            # 지역 추출
            region_match = re.search(r'([가-힣]+(?:구|동))', query)
            if region_match:
                search_params["region"] = region_match.group(1)

            # 매물 종류
            if "아파트" in query:
                search_params["property_type"] = "APARTMENT"
            elif "오피스텔" in query:
                search_params["property_type"] = "OFFICETEL"
            elif "빌라" in query or "다세대" in query:
                search_params["property_type"] = "VILLA"

            # 가격 범위
            price_match = re.search(r'(\d+)억\s*이하', query)
            if price_match:
                search_params["max_price"] = int(price_match.group(1)) * 100000000

            price_match = re.search(r'(\d+)억\s*이상', query)
            if price_match:
                search_params["min_price"] = int(price_match.group(1)) * 100000000

            # 면적 범위
            area_match = re.search(r'(\d+)평\s*이상', query)
            if area_match:
                search_params["min_area"] = float(area_match.group(1)) * 3.3058

            area_match = re.search(r'(\d+)평\s*이하', query)
            if area_match:
                search_params["max_area"] = float(area_match.group(1)) * 3.3058

            # 플래그
            if any(term in query for term in ["지하철", "역", "학교", "마트", "편의시설"]):
                search_params["include_nearby"] = True

            if any(term in query for term in ["실거래가", "거래내역", "매매가"]):
                search_params["include_transactions"] = True

            if any(term in query for term in ["중개사", "agent", "직거래"]):
                search_params["include_agent"] = True

        elif tool_name == "building_registry":
            # 주소 추출
            import re

            # 패턴 1: "서울시 강남구 역삼동 123-45" 형태
            address_match = re.search(r'([가-힣]+[시도])\s*([가-힣]+[시군구])\s*([가-힣]+[읍면동])\s*([\d-]+)', query)

            # 패턴 2: "강남구 역삼동 123-45" 형태 (시도 생략)
            if not address_match:
                address_match = re.search(r'([가-힣]+[시군구])\s*([가-힣]+[읍면동])\s*([\d-]+)', query)

            if address_match:
                groups = address_match.groups()
                if len(groups) == 4:
                    search_params["address"] = f"{groups[0]} {groups[1]} {groups[2]} {groups[3]}"
                else:
                    search_params["address"] = f"{groups[0]} {groups[1]} {groups[2]}"

            # 건물명 추출 (간단한 패턴)
            # "현대쉴러하우스", "래미안" 등
            property_name_match = re.search(r'([가-힣]+(?:아파트|빌라|오피스텔|타워|하우스|팰리스|자이|래미안|푸르지오|힐스테이트))', query)
            if property_name_match:
                search_params["property_name"] = property_name_match.group(1)

        logger.info(f"[Parameter Extraction] Fallback result: {search_params}")
        return search_params

    async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        결과 집계 노드
        여러 검색 결과를 통합
        """
        logger.info("[SearchTeam] Aggregating results")

        # 결과 집계
        total_results = 0
        sources = []

        if state.get("legal_results"):
            total_results += len(state["legal_results"])
            sources.append("legal_db")

        if state.get("real_estate_results"):
            total_results += len(state["real_estate_results"])
            sources.append("real_estate_api")

        if state.get("loan_results"):
            total_results += len(state["loan_results"])
            sources.append("loan_service")

        if state.get("property_search_results"):
            total_results += len(state["property_search_results"])
            sources.append("property_db")

        if state.get("building_registry_results"):
            total_results += len(state["building_registry_results"])
            sources.append("building_registry_api")

        # Terminology 결과 집계 (추가)
        if state.get("terminology_results"):
            total_results += len(state["terminology_results"])
            sources.append("terminology_db")

        # Infrastructure 결과 집계 2025.10.18 추가
        infrastructure_count = 0
        if state.get("infrastructure_results"):
            infra_data = state["infrastructure_results"]
            logger.info(f"[SearchTeam] Found infrastructure_results in state: {type(infra_data)}, keys: {list(infra_data.keys()) if isinstance(infra_data, dict) else 'N/A'}")

            for category in infra_data.values():
                if isinstance(category, dict):
                    for facilities in category.values():
                        if isinstance(facilities, list):
                            infrastructure_count += len(facilities)

            logger.info(f"[SearchTeam] Infrastructure count: {infrastructure_count}")

            if infrastructure_count > 0:
                total_results += infrastructure_count
                sources.append("infrastructure_api")
        else:
            logger.warning("[SearchTeam] No infrastructure_results found in state!")

        state["total_results"] = total_results
        state["sources_used"] = sources

        # 통합 결과 생성
        state["aggregated_results"] = {
            "total_count": total_results,
            "by_type": {
                "legal": len(state.get("legal_results", [])),
                "real_estate": len(state.get("real_estate_results", [])),
                "loan": len(state.get("loan_results", [])),
                "property_search": len(state.get("property_search_results", [])),
                "infrastructure": infrastructure_count,
                "building_registry": len(state.get("building_registry_results", [])),
                "terminology": len(state.get("terminology_results", []))
            },
            "sources": sources,
            "keywords_used": state.get("keywords", {})
        }

        logger.info(f"[SearchTeam] Aggregated {total_results} results from {len(sources)} sources")
        return state

    async def finalize_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        최종화 노드
        상태 정리 및 완료 처리
        """
        logger.info("[SearchTeam] Finalizing")

        state["end_time"] = datetime.now()

        if state.get("start_time"):
            elapsed = (state["end_time"] - state["start_time"]).total_seconds()
            state["search_time"] = elapsed

        # 상태 결정
        if state.get("error"):
            state["status"] = "failed"
        elif state.get("total_results", 0) > 0:
            state["status"] = "completed"
        else:
            state["status"] = "completed"  # 결과가 없어도 완료로 처리

        logger.info(f"[SearchTeam] Completed with status: {state['status']}")
        return state

    async def execute(
        self,
        shared_state: SharedState,
        search_scope: Optional[List[str]] = None,
        keywords: Optional[Dict] = None
    ) -> SearchTeamState:
        """
        SearchTeam 실행

        Args:
            shared_state: 공유 상태
            search_scope: 검색 범위
            keywords: 검색 키워드

        Returns:
            검색 팀 상태
        """
        # 초기 상태 생성
        initial_state = SearchTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            keywords=keywords or SearchKeywords(legal=[], real_estate=[], loan=[], general=[]),
            search_scope=search_scope or [],
            filters={},
            legal_results=[],
            real_estate_results=[],
            loan_results=[],
            property_search_results=[],  # 개별 매물 검색 결과
            infrastructure_results=None,  # 주변 인프라 검색 결과
            building_registry_results=[],  # 건축물 대장 검색 결과
            aggregated_results={},
            total_results=0,
            search_time=0.0,
            sources_used=[],
            search_progress={},
            start_time=None,
            end_time=None,
            error=None,
            current_search=None,
            execution_strategy=None
        )

        # 서브그래프 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"SearchTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state


# 테스트 코드
if __name__ == "__main__":
    async def test_search_team():
        from app.service_agent.foundation.separated_states import StateManager

        # SearchTeam 초기화
        search_team = SearchTeamSupervisor()

        # 테스트 쿼리
        queries = [
            "전세금 5% 인상 가능한가요?",
            "강남구 아파트 시세",
            "주택담보대출 한도"
        ]

        for query in queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print("-"*60)

            # 공유 상태 생성
            shared_state = StateManager.create_shared_state(
                query=query,
                session_id="test_search_team"
            )

            # SearchTeam 실행
            result = await search_team.execute(shared_state)

            print(f"Status: {result['status']}")
            print(f"Total results: {result.get('total_results', 0)}")
            print(f"Sources used: {result.get('sources_used', [])}")
            print(f"Search time: {result.get('search_time', 0):.2f}s")

            if result.get("aggregated_results"):
                print(f"Results by type: {result['aggregated_results']['by_type']}")

    import asyncio
    asyncio.run(test_search_team())