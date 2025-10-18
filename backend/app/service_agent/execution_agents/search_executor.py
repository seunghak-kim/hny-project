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

    def __init__(self, llm_context=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
        """
        self.llm_context = llm_context

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

        # Decision Logger 초기화
        try:
            self.decision_logger = DecisionLogger()
        except Exception as e:
            logger.warning(f"DecisionLogger initialization failed: {e}")
            self.decision_logger = None

        try:
            from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
            self.legal_search_tool = HybridLegalSearch()
            logger.info("HybridLegalSearch initialized successfully")
        except Exception as e:
            logger.warning(f"HybridLegalSearch initialization failed: {e}")

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

            logger.info(f"LLM Keyword Extraction: {result}")

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

            result = await self.llm_service.complete_json_async(
                prompt_name="tool_selection_search",  # search 전용 prompt
                variables={
                    "query": query,  # 키워드 없이 원본 query만
                    "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
                },
                temperature=0.1
            )

            logger.info(f"LLM Tool Selection: {result}")

            selected_tools = result.get("selected_tools", [])
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 0.0)

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
                except Exception as e:
                    logger.warning(f"Failed to log tool decision: {e}")

            return {
                "selected_tools": selected_tools,
                "reasoning": reasoning,
                "confidence": confidence,
                "decision_id": decision_id
            }

        except Exception as e:
            logger.error(f"LLM tool selection failed: {e}")
            return self._select_tools_with_fallback(keywords=keywords, query=query)

    def _select_tools_with_fallback(self, keywords: SearchKeywords = None, query: str = "") -> Dict[str, Any]:
        """
        규칙 기반 fallback tool 선택
        LLM 실패 시 사용 (안전망)
        """
        # 모든 tool을 사용하는 것이 가장 안전
        available_tools = self._get_available_tools()
        scope = list(available_tools.keys())

        if not scope:
            # tool이 하나도 없으면 빈 배열
            scope = []

        reasoning = "Fallback: using all available tools for safety"
        confidence = 0.3

        # Decision Logger에 기록 (fallback도 기록)
        decision_id = None
        if self.decision_logger and query:
            try:
                decision_id = self.decision_logger.log_tool_decision(
                    agent_type="search",
                    query=query,
                    available_tools=available_tools,
                    selected_tools=scope,
                    reasoning=reasoning,
                    confidence=confidence
                )
            except Exception as e:
                logger.warning(f"Failed to log fallback tool decision: {e}")

        return {
            "selected_tools": scope,
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

                # 검색 파라미터 구성
                search_params = {
                    "limit": 10
                }

                # 임차인 보호 조항 필터
                if any(term in query for term in ["임차인", "전세", "임대", "보증금"]):
                    search_params["is_tenant_protection"] = True

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

        # === 3-1. 개별 부동산 매물 검색 (Phase 2) ===
        if "real_estate_search" in selected_tools and self.real_estate_search_tool:
            try:
                logger.info("[SearchTeam] Executing individual real estate property search")

                # 쿼리에서 파라미터 추출 (간단한 패턴 매칭)
                search_params = {}

                # 지역 추출
                regions = ["강남구", "강북구", "강동구", "강서구", "관악구", "광진구", "구로구",
                          "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구",
                          "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구",
                          "은평구", "종로구", "중구", "중랑구"]
                for region in regions:
                    if region in query:
                        search_params["region"] = region
                        break

                # 물건 종류 추출
                if "아파트" in query:
                    search_params["property_type"] = "APARTMENT"
                elif "오피스텔" in query:
                    search_params["property_type"] = "OFFICETEL"
                elif "빌라" in query or "다세대" in query:
                    search_params["property_type"] = "VILLA"

                # 가격 범위 추출 (예: "5억 이하")
                import re
                price_match = re.search(r'(\d+)억\s*이하', query)
                if price_match:
                    max_price = int(price_match.group(1)) * 100000000
                    search_params["max_price"] = max_price

                price_match = re.search(r'(\d+)억\s*이상', query)
                if price_match:
                    min_price = int(price_match.group(1)) * 100000000
                    search_params["min_price"] = min_price

                # 면적 범위 추출 (예: "80평 이상")
                area_match = re.search(r'(\d+)평\s*이상', query)
                if area_match:
                    min_area = float(area_match.group(1)) * 3.3058  # 평 to ㎡
                    search_params["min_area"] = min_area

                area_match = re.search(r'(\d+)평\s*이하', query)
                if area_match:
                    max_area = float(area_match.group(1)) * 3.3058
                    search_params["max_area"] = max_area

                # 주변 시설 정보 포함 여부
                if any(term in query for term in ["지하철", "역", "학교", "마트", "편의시설"]):
                    search_params["include_nearby"] = True

                # 실거래가 내역 포함 여부
                if any(term in query for term in ["실거래가", "거래내역", "매매가"]):
                    search_params["include_transactions"] = True

                # 중개사 정보 포함 여부 (Q5: 조건부)
                if any(term in query for term in ["중개사", "agent", "직거래", "공인중개사"]):
                    search_params["include_agent"] = True

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

        # === 4. SearchAgent 실행 (추가 검색 필요 시) ===
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

        state["total_results"] = total_results
        state["sources_used"] = sources

        # 통합 결과 생성
        state["aggregated_results"] = {
            "total_count": total_results,
            "by_type": {
                "legal": len(state.get("legal_results", [])),
                "real_estate": len(state.get("real_estate_results", [])),
                "loan": len(state.get("loan_results", [])),
                "property_search": len(state.get("property_search_results", []))
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