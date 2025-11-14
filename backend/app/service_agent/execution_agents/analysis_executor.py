"""
Analysis Executor - 데이터 분석 실행 Agent
수집된 데이터를 분석하여 인사이트와 추천사항을 생성
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.separated_states import (
    AnalysisTeamState,
    AnalysisInput,
    AnalysisMetrics,
    AnalysisInsight,
    AnalysisReport,
    SharedState
)
from app.service_agent.llm_manager import LLMService
from app.service_agent.foundation.decision_logger import DecisionLogger

# Import analysis tools
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool
)

logger = logging.getLogger(__name__)


class AnalysisExecutor:
    """
    분석 실행 Agent
    데이터 분석 및 보고서 생성 작업을 실행
    """

    def __init__(self, llm_context=None, progress_callback=None):
        """초기화"""
        self.llm_context = llm_context
        self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
        self.progress_callback = progress_callback  # 🆕 Store parent's WebSocket callback
        self.team_name = "analysis"

        # 분석 도구 초기화
        self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
        self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
        self.roi_tool = ROICalculatorTool()
        self.loan_tool = LoanSimulatorTool()
        self.policy_tool = PolicyMatcherTool()

        # LegalSearch tool 초기화 (Execute 병합)
        try:
            from app.service_agent.tools import LegalSearch
            self.legal_search_tool = LegalSearch()
            logger.info("LegalSearch initialized successfully in AnalysisExecutor")
        except Exception as e:
            logger.warning(f"LegalSearch initialization failed in AnalysisExecutor: {e}")
            self.legal_search_tool = None

        # Decision Logger 초기화
        try:
            self.decision_logger = DecisionLogger()
        except Exception as e:
            logger.warning(f"DecisionLogger initialization failed: {e}")
            self.decision_logger = None

        # 분석 메서드 매핑
        self.analysis_methods = {
            "comprehensive": self._comprehensive_analysis,
            "market": self._market_analysis,
            "risk": self._risk_analysis,
            "comparison": self._comparison_analysis,
            "contract": self._contract_analysis,
            "investment": self._investment_analysis,
            "loan": self._loan_analysis,
            "policy": self._policy_analysis
        }

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _get_available_analysis_tools(self) -> Dict[str, Any]:
        """
        현재 AnalysisExecutor에서 사용 가능한 분석 tool 정보를 동적으로 수집
        하드코딩 없이 실제 초기화된 tool만 반환
        """
        tools = {}

        if self.contract_tool:
            tools["contract_analysis"] = {
                "name": "contract_analysis",
                "description": "계약서 조항 분석 및 위험요소 탐지",
                "capabilities": [
                    "계약서 위험 조항 검토",
                    "법적 문제점 식별",
                    "특약사항 분석",
                    "계약 조건 적정성 평가"
                ],
                "available": True
            }

        if self.market_tool:
            tools["market_analysis"] = {
                "name": "market_analysis",
                "description": "시장 동향 및 가격 적정성 분석",
                "capabilities": [
                    "가격 적정성 평가",
                    "시장 동향 분석",
                    "지역 비교 분석",
                    "투자 가치 평가"
                ],
                "available": True
            }

        if self.roi_tool:
            tools["roi_calculator"] = {
                "name": "roi_calculator",
                "description": "투자수익률 계산 및 현금흐름 분석",
                "capabilities": [
                    "ROI 계산",
                    "수익률 분석",
                    "현금흐름 시뮬레이션",
                    "투자 대비 수익 평가"
                ],
                "available": True
            }

        if self.loan_tool:
            tools["loan_simulator"] = {
                "name": "loan_simulator",
                "description": "대출 한도 및 금리 시뮬레이션 (LTV, DTI, DSR)",
                "capabilities": [
                    "대출 한도 계산",
                    "LTV/DTI/DSR 시뮬레이션",
                    "월 상환액 계산",
                    "대출 가능성 평가"
                ],
                "available": True
            }

        if self.policy_tool:
            tools["policy_matcher"] = {
                "name": "policy_matcher",
                "description": "정부 지원 정책 매칭 및 혜택 분석",
                "capabilities": [
                    "청년 정책 매칭",
                    "신혼부부 정책 매칭",
                    "자격 조건 확인",
                    "혜택 금액 계산"
                ],
                "available": True
            }

        # LegalSearch tool (Execute 병합)
        if self.legal_search_tool:
            tools["legal_search"] = {
                "name": "legal_search",
                "description": "법률 및 시행령 검색, 법률 조항 분석",
                "capabilities": [
                    "법률 조문 검색",
                    "시행령 검색",
                    "부동산 관련 법률 조회",
                    "법률 해석 및 적용"
                ],
                "available": True
            }

        return tools

    async def _select_tools_with_llm(
        self,
        query: str,
        collected_data_summary: Dict = None
    ) -> Dict[str, Any]:
        """
        LLM을 사용한 분석 tool 선택

        Args:
            query: 사용자 쿼리
            collected_data_summary: 수집된 데이터 요약 (optional)

        Returns:
            {
                "selected_tools": ["contract_analysis", "market_analysis"],
                "reasoning": "...",
                "confidence": 0.9
            }
        """
        if not self.llm_service:
            logger.warning("LLM service not available, using fallback")
            return self._select_tools_with_fallback(query=query)

        try:
            # 동적으로 사용 가능한 분석 tool 정보 수집
            available_tools = self._get_available_analysis_tools()

            # 수집된 데이터 요약 생성
            if not collected_data_summary:
                collected_data_summary = {"status": "no data collected yet"}

            result = await self.llm_service.complete_json_async(
                prompt_name="tool_selection_analysis",  # analysis 전용 prompt
                variables={
                    "query": query,
                    "collected_data_summary": json.dumps(collected_data_summary, ensure_ascii=False),
                    "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
                },
                temperature=0.1
            )

            logger.info(f"LLM Analysis Tool Selection: {result}")

            selected_tools = result.get("selected_tools", [])
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 0.0)

            # Decision Logger에 기록
            decision_id = None
            if self.decision_logger:
                try:
                    decision_id = self.decision_logger.log_tool_decision(
                        agent_type="analysis",
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
            logger.error(f"LLM analysis tool selection failed: {e}")
            return self._select_tools_with_fallback(query=query)

    def _select_tools_with_fallback(self, query: str = "") -> Dict[str, Any]:
        """
        규칙 기반 fallback tool 선택
        LLM 실패 시 사용 (안전망)
        """
        # 모든 분석 tool을 사용하는 것이 가장 안전
        available_tools = self._get_available_analysis_tools()
        scope = list(available_tools.keys())

        if not scope:
            scope = []

        reasoning = "Fallback: using all available analysis tools for comprehensive coverage"
        confidence = 0.3

        # Decision Logger에 기록 (fallback도 기록)
        decision_id = None
        if self.decision_logger and query:
            try:
                decision_id = self.decision_logger.log_tool_decision(
                    agent_type="analysis",
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

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(AnalysisTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_analysis_node)
        workflow.add_node("preprocess", self.preprocess_data_node)
        workflow.add_node("analyze", self.analyze_data_node)
        workflow.add_node("generate_insights", self.generate_insights_node)
        workflow.add_node("create_report", self.create_report_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START, "prepare")
        workflow.add_edge("prepare", "preprocess")
        workflow.add_edge("preprocess", "analyze")
        workflow.add_edge("analyze", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("AnalysisTeam subgraph built successfully")

    async def prepare_analysis_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """분석 준비 노드"""
        logger.info("[AnalysisTeam] Preparing analysis")

        # 🆕 Step Progress: Step 0 (데이터 수집) - Start
        await self._update_step_progress(state, step_index=0, status="in_progress", progress=0)

        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()
        state["analysis_status"] = "preparing"
        state["analysis_progress"] = {"current": "prepare", "percent": 0.0}

        if not state.get("analysis_type"):
            state["analysis_type"] = "comprehensive"

        logger.info(f"[AnalysisTeam] Analysis type: {state['analysis_type']}")

        # 🆕 Step Progress: Step 0 (데이터 수집) - Complete
        await self._update_step_progress(state, step_index=0, status="completed", progress=100)

        return state

    async def preprocess_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """데이터 전처리 노드"""
        logger.info("[AnalysisTeam] Preprocessing data")

        # 🆕 Step Progress: Step 1 (데이터 분석) - Start
        await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)

        state["preprocessing_status"] = "in_progress"
        state["analysis_progress"] = {"current": "preprocess", "percent": 0.1}

        # 입력 데이터를 그대로 전달
        preprocessed = {}
        for input_item in state.get("input_data", []):
            preprocessed[input_item["data_source"]] = input_item.get("data", input_item.get("raw_data", {}))

        state["preprocessed_data"] = preprocessed
        state["preprocessing_status"] = "completed"
        state["analysis_progress"] = {"current": "preprocess", "percent": 0.2}

        # 🆕 Step Progress: Step 1 (데이터 분석) - Complete
        await self._update_step_progress(state, step_index=1, status="completed", progress=100)

        return state

    async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        실제 데이터 분석 노드
        새로운 analysis tools를 사용하여 실제 분석 수행
        """
        logger.info("[AnalysisTeam] Analyzing data with new analysis tools")

        # 🆕 Step Progress: Step 2 (패턴 인식) - Start
        await self._update_step_progress(state, step_index=2, status="in_progress", progress=0)

        import time
        start_time = time.time()

        state["analysis_status"] = "analyzing"
        state["analysis_progress"] = {"current": "analyze", "percent": 0.3}

        try:
            preprocessed_data = state.get("preprocessed_data", {})
            shared_context = state.get("shared_context", {})
            query = shared_context.get("user_query", "") or shared_context.get("query", "")
            analysis_type = state.get("analysis_type", "comprehensive")

            # LLM 기반 도구 선택
            collected_data_summary = {
                "has_legal_data": bool(preprocessed_data.get("legal_search")),
                "has_market_data": bool(preprocessed_data.get("real_estate_search")),
                "has_loan_data": bool(preprocessed_data.get("loan_search")),
                "has_contract": bool(preprocessed_data.get("contract")),
                "data_types": list(preprocessed_data.keys())
            }

            tool_selection = await self._select_tools_with_llm(query, collected_data_summary)
            selected_tools = tool_selection.get("selected_tools", [])
            decision_id = tool_selection.get("decision_id")

            logger.info(
                f"[AnalysisTeam] LLM selected tools: {selected_tools}, "
                f"confidence: {tool_selection.get('confidence')}"
            )

            # 실행 결과 추적
            execution_results = {}
            results = {}

            # LLM이 선택한 도구들을 실행
            if "market_analysis" in selected_tools:
                try:
                    property_data = self._extract_property_data(preprocessed_data, query)
                    market_data = preprocessed_data.get("real_estate_search", {})
                    results["market"] = await self.market_tool.execute(
                        property_data=property_data,
                        market_data=market_data
                    )
                    logger.info("[AnalysisTools] Market analysis completed")
                    execution_results["market_analysis"] = {
                        "status": "success",
                        "has_result": bool(results["market"])
                    }
                except Exception as e:
                    logger.error(f"Market analysis failed: {e}")
                    execution_results["market_analysis"] = {
                        "status": "error",
                        "error": str(e)
                    }

            if "contract_analysis" in selected_tools:
                try:
                    contract_text = preprocessed_data.get("contract", "")
                    legal_refs = preprocessed_data.get("legal_search", [])
                    if contract_text:
                        results["contract"] = await self.contract_tool.execute(
                            contract_text=contract_text,
                            legal_references=legal_refs
                        )
                        logger.info("[AnalysisTools] Contract analysis completed")
                        execution_results["contract_analysis"] = {
                            "status": "success",
                            "has_result": bool(results["contract"])
                        }
                    else:
                        execution_results["contract_analysis"] = {
                            "status": "skipped",
                            "reason": "no contract data"
                        }
                except Exception as e:
                    logger.error(f"Contract analysis failed: {e}")
                    execution_results["contract_analysis"] = {
                        "status": "error",
                        "error": str(e)
                    }

            if "roi_calculator" in selected_tools:
                try:
                    property_price = self._extract_price(preprocessed_data, query)
                    if property_price:
                        results["roi"] = await self.roi_tool.execute(
                            property_price=property_price,
                            monthly_rent=self._extract_rent(preprocessed_data, query)
                        )
                        logger.info("[AnalysisTools] ROI calculation completed")
                        execution_results["roi_calculator"] = {
                            "status": "success",
                            "has_result": bool(results["roi"])
                        }
                    else:
                        execution_results["roi_calculator"] = {
                            "status": "skipped",
                            "reason": "no price data"
                        }
                except Exception as e:
                    logger.error(f"ROI calculation failed: {e}")
                    execution_results["roi_calculator"] = {
                        "status": "error",
                        "error": str(e)
                    }

            if "loan_simulator" in selected_tools:
                try:
                    property_price = self._extract_price(preprocessed_data, query)
                    income = self._extract_income(preprocessed_data, query)
                    if property_price and income:
                        results["loan"] = await self.loan_tool.execute(
                            property_price=property_price,
                            annual_income=income
                        )
                        logger.info("[AnalysisTools] Loan simulation completed")
                        execution_results["loan_simulator"] = {
                            "status": "success",
                            "has_result": bool(results["loan"])
                        }
                    else:
                        execution_results["loan_simulator"] = {
                            "status": "skipped",
                            "reason": "insufficient data"
                        }
                except Exception as e:
                    logger.error(f"Loan simulation failed: {e}")
                    execution_results["loan_simulator"] = {
                        "status": "error",
                        "error": str(e)
                    }

            if "policy_matcher" in selected_tools:
                try:
                    user_profile = self._extract_user_profile(preprocessed_data, query)
                    results["policy"] = await self.policy_tool.execute(
                        user_profile=user_profile
                    )
                    logger.info("[AnalysisTools] Policy matching completed")
                    execution_results["policy_matcher"] = {
                        "status": "success",
                        "has_result": bool(results["policy"])
                    }
                except Exception as e:
                    logger.error(f"Policy matching failed: {e}")
                    execution_results["policy_matcher"] = {
                        "status": "error",
                        "error": str(e)
                    }

            # 맞춤 분석 (전세금 인상률 등)
            results["custom"] = self._perform_custom_analysis(query, preprocessed_data)
            if results["custom"]["type"] != "general":
                logger.info(f"[CustomAnalysis] {results['custom']['type']} performed")

            # 결과 저장
            state["raw_analysis"] = results
            state["analysis_status"] = "completed"
            state["analysis_progress"] = {"current": "analyze", "percent": 0.6}

            # 실행 시간 계산 및 결과 로깅
            total_execution_time_ms = int((time.time() - start_time) * 1000)

            if decision_id and self.decision_logger:
                try:
                    # 전체 성공 여부 판단
                    success = all(
                        r.get("status") in ["success", "skipped"]
                        for r in execution_results.values()
                    )

                    self.decision_logger.update_tool_execution_results(
                        decision_id=decision_id,
                        execution_results=execution_results,
                        total_execution_time_ms=total_execution_time_ms,
                        success=success
                    )

                    logger.info(
                        f"[AnalysisTeam] Logged execution results: "
                        f"decision_id={decision_id}, success={success}, "
                        f"time={total_execution_time_ms}ms"
                    )
                except Exception as e:
                    logger.warning(f"Failed to log execution results: {e}")

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            state["analysis_status"] = "failed"
            state["error"] = str(e)

        # 🆕 Step Progress: Step 2 (패턴 인식) - Complete
        await self._update_step_progress(state, step_index=2, status="completed", progress=100)

        return state

    def _extract_property_data(self, data: Dict, query: str) -> Dict:
        """부동산 데이터 추출"""
        property_data = {
            "address": data.get("address", ""),
            "type": "apartment",
            "size": 84.5,
            "price": 0
        }

        # 쿼리에서 지역 추출
        if "강남" in query:
            property_data["address"] = "서울시 강남구"
        elif "서초" in query:
            property_data["address"] = "서울시 서초구"

        # 데이터에서 가격 정보 추출
        if "real_estate_search" in data:
            prices = data["real_estate_search"].get("results", [])
            if prices:
                property_data["price"] = prices[0].get("price", 0)

        return property_data

    def _extract_price(self, data: Dict, query: str) -> float:
        """가격 정보 추출"""
        # 쿼리에서 금액 추출
        amounts = re.findall(r'(\d+)억', query)
        if amounts:
            return float(amounts[0]) * 100000000

        # 데이터에서 추출
        if "real_estate_search" in data:
            results = data["real_estate_search"].get("results", [])
            if results:
                return results[0].get("price", 0)

        return 0

    def _extract_rent(self, data: Dict, query: str) -> float:
        """월세 정보 추출"""
        # 쿼리에서 월세 추출
        rents = re.findall(r'월세.*?(\d+)만', query)
        if rents:
            return float(rents[0]) * 10000
        return 0

    def _extract_income(self, data: Dict, query: str) -> float:
        """소득 정보 추출"""
        # 기본값
        return 100000000  # 1억

    def _extract_user_profile(self, data: Dict, query: str) -> Dict:
        """사용자 프로필 추출"""
        profile = {
            "age": 32,
            "annual_income": 60000000,
            "has_house": False,
            "region": "서울"
        }

        # 쿼리에서 정보 추출
        if "청년" in query:
            profile["age"] = 28
        elif "신혼" in query:
            profile["marriage_years"] = 2

        return profile

    def _perform_custom_analysis(self, query: str, data: Dict) -> Dict:
        """쿼리 기반 맞춤 분석"""

        # 전세금 인상 관련 쿼리 감지
        if "전세금" in query and any(x in query for x in ["올", "인상", "올려"]):
            return self._analyze_rent_increase(query, data)

        return {"type": "general"}

    def _analyze_rent_increase(self, query: str, data: Dict) -> Dict:
        """전세금 인상률 계산"""

        # 쿼리에서 금액 추출 (예: "3억을 10억으로")
        amounts = re.findall(r'(\d+)억', query)

        if len(amounts) >= 2:
            old_amount = float(amounts[0])
            new_amount = float(amounts[1])
            increase_rate = ((new_amount - old_amount) / old_amount) * 100

            return {
                "type": "rent_increase_analysis",
                "old_amount": f"{old_amount}억",
                "new_amount": f"{new_amount}억",
                "increase_amount": f"{new_amount - old_amount}억",
                "increase_rate": f"{increase_rate:.1f}%",
                "legal_limit": "5%",
                "is_legal": increase_rate <= 5,
                "assessment": f"요청된 인상률 {increase_rate:.1f}%는 법정 한도 5%를 {'초과' if increase_rate > 5 else '준수'}합니다.",
                "recommendation": "법정 한도를 초과하는 인상은 거부할 수 있습니다." if increase_rate > 5 else "법정 범위 내 인상입니다."
            }

        return {"type": "rent_increase_analysis", "status": "insufficient_data"}

    async def generate_insights_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """인사이트 생성 노드"""
        logger.info("[AnalysisTeam] Generating insights")

        # 🆕 Step Progress: Step 3 (인사이트 생성) - Start
        await self._update_step_progress(state, step_index=3, status="in_progress", progress=0)

        state["analysis_progress"] = {"current": "insights", "percent": 0.7}

        # LLM 사용 가능 시 LLM 기반 인사이트 생성
        if self.llm_context and self.llm_context.api_key:
            try:
                insights = await self._generate_insights_with_llm(state)
            except Exception as e:
                logger.warning(f"LLM insight generation failed, using fallback: {e}")
                analysis_method = self.analysis_methods.get(
                    state.get("analysis_type", "comprehensive"),
                    self._comprehensive_analysis
                )
                insights = analysis_method(state)
        else:
            analysis_method = self.analysis_methods.get(
                state.get("analysis_type", "comprehensive"),
                self._comprehensive_analysis
            )
            insights = analysis_method(state)

        state["insights"] = insights
        state["analysis_progress"] = {"current": "insights", "percent": 0.8}
        state["confidence_score"] = self._calculate_confidence(state)

        # 🆕 Step Progress: Step 3 (인사이트 생성) - Complete
        await self._update_step_progress(state, step_index=3, status="completed", progress=100)

        return state

    async def _generate_insights_with_llm(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """LLM을 사용한 인사이트 생성"""
        raw_analysis = state.get("raw_analysis", {})
        analysis_type = state.get("analysis_type", "comprehensive")
        shared_context = state.get("shared_context", {})
        query = shared_context.get("user_query", "") or shared_context.get("query", "")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="insight_generation",
                variables={
                    "query": query,
                    "analysis_type": analysis_type,
                    "raw_analysis": json.dumps(raw_analysis, ensure_ascii=False, indent=2)
                },
                temperature=0.3
            )

            logger.info(f"LLM Insight Generation: {len(result.get('insights', []))} insights generated")

            insights = []
            for insight_data in result.get("insights", []):
                insight = AnalysisInsight(
                    insight_type=insight_data.get("type", "key_finding"),
                    content=f"{insight_data.get('title', '')}: {insight_data.get('description', '')}",
                    confidence=insight_data.get("confidence", 0.7),
                    supporting_data=insight_data.get("supporting_evidence", {})
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            raise

    def _comprehensive_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """종합 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        # custom 분석 결과 확인
        if "custom" in raw_analysis and raw_analysis["custom"]["type"] == "rent_increase_analysis":
            custom = raw_analysis["custom"]
            insights.append(AnalysisInsight(
                insight_type="rent_increase",
                content=custom.get("assessment", ""),
                confidence=0.95,
                supporting_data=custom
            ))

        # 시장 분석 결과
        if "market" in raw_analysis and raw_analysis["market"].get("status") == "success":
            market = raw_analysis["market"]
            insights.append(AnalysisInsight(
                insight_type="market_condition",
                content=f"시장 상황: {market.get('market_conditions', {}).get('overall', 'N/A')}",
                confidence=0.8,
                supporting_data=market.get("metrics", {})
            ))

        return insights

    def _market_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """시장 분석"""
        return self._comprehensive_analysis(state)

    def _risk_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """리스크 분석"""
        return self._comprehensive_analysis(state)

    def _comparison_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """비교 분석"""
        return self._comprehensive_analysis(state)

    def _contract_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """계약서 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        if "contract" in raw_analysis and raw_analysis["contract"].get("status") == "success":
            contract = raw_analysis["contract"]

            # 위험 요소
            for risk in contract.get("risks", [])[:3]:
                insights.append(AnalysisInsight(
                    insight_type="contract_risk",
                    content=f"{risk.get('keyword', '')}: {risk.get('suggestion', '')}",
                    confidence=0.85,
                    supporting_data=risk
                ))

            # 추천사항
            for rec in contract.get("recommendations", [])[:2]:
                insights.append(AnalysisInsight(
                    insight_type="recommendation",
                    content=rec.get("detail", ""),
                    confidence=0.8,
                    supporting_data=rec
                ))

        return insights

    def _investment_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """투자 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        if "roi" in raw_analysis and raw_analysis["roi"].get("status") == "success":
            roi = raw_analysis["roi"]
            metrics = roi.get("roi_metrics", {})

            insights.append(AnalysisInsight(
                insight_type="roi_analysis",
                content=f"투자수익률 {metrics.get('roi_percentage', 0)}%, 연평균 {metrics.get('annual_return', 0)}%",
                confidence=0.9,
                supporting_data=metrics
            ))

            evaluation = roi.get("evaluation", {})
            insights.append(AnalysisInsight(
                insight_type="investment_grade",
                content=f"{evaluation.get('grade', '')}: {evaluation.get('recommendation', '')}",
                confidence=0.85,
                supporting_data=evaluation
            ))

        return insights

    def _loan_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """대출 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        if "loan" in raw_analysis and raw_analysis["loan"].get("status") == "success":
            loan = raw_analysis["loan"]
            max_loan = loan.get("max_loan", {})

            insights.append(AnalysisInsight(
                insight_type="loan_limit",
                content=f"최대 대출 한도: {max_loan.get('loan_amount', 0)/100000000:.1f}억 (LTV {max_loan.get('ltv_ratio', 0)}%)",
                confidence=0.9,
                supporting_data=max_loan
            ))

            repayment = loan.get("repayment_plan", {})
            insights.append(AnalysisInsight(
                insight_type="repayment",
                content=f"월 상환액: {repayment.get('monthly_payment', 0)/10000:.0f}만원 (소득 대비 {repayment.get('payment_burden_pct', 0)}%)",
                confidence=0.85,
                supporting_data=repayment
            ))

        return insights

    def _policy_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """정책 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        if "policy" in raw_analysis and raw_analysis["policy"].get("status") == "success":
            policy = raw_analysis["policy"]

            # 상위 3개 정책
            for p in policy.get("matched_policies", [])[:3]:
                insights.append(AnalysisInsight(
                    insight_type="policy_match",
                    content=f"{p.get('name', '')}: {p.get('priority_reason', '')}",
                    confidence=p.get("match_score", 50) / 100,
                    supporting_data=p
                ))

            # 총 혜택
            benefits = policy.get("benefit_summary", {})
            if benefits.get("max_loan_amount"):
                insights.append(AnalysisInsight(
                    insight_type="total_benefit",
                    content=f"최대 대출 {benefits['max_loan_amount']/100000000:.1f}억, 최저금리 {benefits.get('min_interest_rate', 0)}%",
                    confidence=0.8,
                    supporting_data=benefits
                ))

        return insights

    def _calculate_confidence(self, state: AnalysisTeamState) -> float:
        """신뢰도 계산"""
        base_confidence = 0.5

        if state.get("input_data"):
            base_confidence += 0.1 * min(len(state["input_data"]), 3)

        if state.get("analysis_status") == "completed":
            base_confidence += 0.2

        return min(base_confidence, 1.0)

    async def create_report_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """보고서 생성 노드"""
        logger.info("[AnalysisTeam] Creating report")

        # 🆕 Step Progress: Step 4 (리포트 작성) - Start
        await self._update_step_progress(state, step_index=4, status="in_progress", progress=0)

        state["analysis_progress"] = {"current": "report", "percent": 0.9}

        report = AnalysisReport(
            title=f"{state.get('analysis_type', '종합')} 분석 보고서",
            summary=self._generate_summary(state),
            key_findings=self._extract_key_findings(state),
            metrics=state.get("metrics", {}),
            insights=state.get("insights", []),
            visualizations=[],
            recommendations=self._compile_recommendations(state),
            generated_at=datetime.now()
        )

        state["report"] = report
        state["analysis_progress"] = {"current": "report", "percent": 1.0}

        # 🆕 Step Progress: Step 4 (리포트 작성) - Complete
        await self._update_step_progress(state, step_index=4, status="completed", progress=100)

        return state

    def _generate_summary(self, state: AnalysisTeamState) -> str:
        """요약 생성"""
        analysis_type = state.get("analysis_type", "종합")
        insights_count = len(state.get("insights", []))
        confidence = state.get("confidence_score", 0)

        return (f"{analysis_type} 분석을 완료했습니다. "
                f"{insights_count}개의 주요 인사이트를 도출했으며, "
                f"신뢰도는 {confidence:.0%}입니다.")

    def _extract_key_findings(self, state: AnalysisTeamState) -> List[str]:
        """주요 발견사항 추출"""
        findings = []

        for insight in state.get("insights", []):
            if insight.get("confidence", 0) > 0.7:
                findings.append(insight.get("content", ""))

        return findings[:5]

    def _compile_recommendations(self, state: AnalysisTeamState) -> List[str]:
        """추천사항 종합"""
        recommendations = []

        # raw_analysis에서 추천사항 추출
        raw_analysis = state.get("raw_analysis", {})
        if "custom" in raw_analysis and "recommendation" in raw_analysis["custom"]:
            recommendations.append(raw_analysis["custom"]["recommendation"])

        return list(set(recommendations))

    async def finalize_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """최종화 노드"""
        logger.info("[AnalysisTeam] Finalizing")

        state["end_time"] = datetime.now()

        # Calculate analysis time
        if state["start_time"] and state["end_time"]:
            state["analysis_time"] = (state["end_time"] - state["start_time"]).total_seconds()

        if state.get("error"):
            state["status"] = "failed"
        elif state.get("report"):
            state["status"] = "completed"
        else:
            state["status"] = "partial"

        logger.info(f"[AnalysisTeam] Completed with status: {state['status']}")
        return state

    async def _update_step_progress(
        self,
        state: AnalysisTeamState,
        step_index: int,
        status: str,
        progress: int = 0
    ) -> None:
        """
        🆕 Update agent step progress in state AND forward to WebSocket.

        This method writes step progress updates to the state and forwards
        them to the parent graph via WebSocket callback for real-time UI updates.

        Args:
            state: AnalysisTeamState
            step_index: Step index (0-4 for analysis agent's 5 steps)
            status: Step status ("pending", "in_progress", "completed", "failed")
            progress: Progress percentage (0-100)
        """
        # Initialize analysis_step_progress if not exists
        if "analysis_step_progress" not in state:
            state["analysis_step_progress"] = {}

        # Update step progress in state
        state["analysis_step_progress"][f"step_{step_index}"] = {
            "index": step_index,
            "status": status,
            "progress": progress
        }

        logger.debug(f"[AnalysisExecutor] Step {step_index} progress: {status} ({progress}%)")

        # 🆕 Forward to WebSocket via parent callback for real-time UI updates
        if self.progress_callback:
            await self.progress_callback("agent_step_progress", {
                "agentName": "analysis",
                "agentType": "analysis",
                "stepId": f"analysis_step_{step_index + 1}",  # 1-indexed for frontend
                "stepIndex": step_index,
                "status": status,
                "progress": progress
            })
            logger.debug(f"[AnalysisExecutor] Forwarded step {step_index} progress to WebSocket")

    async def execute(
        self,
        shared_state: SharedState,
        analysis_type: str = "comprehensive",
        input_data: Optional[Dict] = None
    ) -> AnalysisTeamState:
        """AnalysisTeam 실행"""
        # 입력 데이터 준비
        analysis_inputs = []
        if input_data:
            for source, data in input_data.items():
                analysis_inputs.append(AnalysisInput(
                    data_source=source,
                    data=data,
                    metadata={}
                ))

        # 초기 상태 생성
        initial_state = AnalysisTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            analysis_type=analysis_type,
            input_data=analysis_inputs,
            raw_analysis={},
            metrics={},
            insights=[],
            report={},
            visualization_data=None,
            recommendations=[],
            confidence_score=0.0,
            analysis_progress={"current": "init", "percent": 0.0},
            start_time=None,
            end_time=None,
            analysis_time=None,
            error=None
        )

        # 서브그래프 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"AnalysisTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state
