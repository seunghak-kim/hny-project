"""
Team-based Supervisor - 팀 기반 서브그래프를 조정하는 메인 Supervisor
SearchTeam, DocumentTeam, AnalysisTeam을 오케스트레이션
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
import asyncio
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Long-term Memory imports
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService
from app.db.postgre_db import get_async_db
from app.core.config import settings

from app.service_agent.foundation.separated_states import (
    MainSupervisorState,
    SharedState,
    StateManager,
    PlanningState
)
from app.service_agent.foundation.context import LLMContext, create_default_llm_context
from app.service_agent.cognitive_agents.planning_agent import PlanningAgent, IntentType, ExecutionStrategy
from app.service_agent.execution_agents import SearchExecutor, DocumentExecutor, AnalysisExecutor
from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import initialize_agent_system
from app.service_agent.foundation.checkpointer import create_checkpointer

logger = logging.getLogger(__name__)


class TeamBasedSupervisor:
    """
    팀 기반 Supervisor
    각 팀을 독립적으로 관리하고 조정
    """

    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
            enable_checkpointing: Checkpointing 활성화 여부
        """
        self.llm_context = llm_context or create_default_llm_context()
        self.enable_checkpointing = enable_checkpointing

        # Agent 시스템 초기화
        initialize_agent_system(auto_register=True)

        # Checkpointer - async 초기화 필요
        self.checkpointer = None
        self._checkpointer_initialized = False
        self._checkpoint_cm = None  # Async context manager for checkpointer

        # Progress Callbacks - WebSocket 실시간 통신용 (State와 분리)
        # session_id → callback 매핑
        # Callable은 직렬화 불가능하므로 State에 포함하지 않음
        self._progress_callbacks: Dict[str, Callable[[str, dict], Awaitable[None]]] = {}

        # Planning Agent
        self.planning_agent = PlanningAgent(llm_context=llm_context)

        # 팀 초기화
        self.teams = {
            "search": SearchExecutor(llm_context=llm_context),
            "document": DocumentExecutor(llm_context=llm_context),
            "analysis": AnalysisExecutor(llm_context=llm_context)
        }

        # 워크플로우 구성 (checkpointer는 나중에 초기화)
        self.app = None
        self._build_graph()

        logger.info(f"TeamBasedSupervisor initialized with 3 teams (checkpointing: {enable_checkpointing})")

    def _get_llm_client(self):
        """LLM 클라이언트 가져오기"""
        try:
            from openai import OpenAI
            if self.llm_context.api_key:
                return OpenAI(api_key=self.llm_context.api_key)
        except:
            pass
        return None

    def _build_graph(self):
        """워크플로우 그래프 구성"""
        workflow = StateGraph(MainSupervisorState)

        # 노드 추가
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute_teams", self.execute_teams_node)
        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 구성
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "planning")

        # 계획 후 라우팅
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "execute": "execute_teams",
                "respond": "generate_response"
            }
        )

        workflow.add_edge("execute_teams", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # Compile without checkpointer initially
        # Checkpointer will be set during async_run if enabled
        self.app = workflow.compile()
        logger.info("Team-based workflow graph built successfully")

    def _route_after_planning(self, state: MainSupervisorState) -> str:
        """계획 후 라우팅"""
        planning_state = state.get("planning_state")

        # 기능 외 질문 필터링
        if planning_state:
            analyzed_intent = planning_state.get("analyzed_intent", {})
            intent_type = analyzed_intent.get("intent_type", "")
            confidence = analyzed_intent.get("confidence", 0.0)

            # IRRELEVANT 또는 낮은 confidence의 UNCLEAR는 바로 응답
            if intent_type == "irrelevant":
                logger.info("[TeamSupervisor] Detected IRRELEVANT query, routing to respond with guidance")
                return "respond"

            if intent_type == "unclear" and confidence < 0.3:
                logger.info(f"[TeamSupervisor] Low confidence UNCLEAR query ({confidence:.2f}), routing to respond")
                return "respond"

        # 정상적인 실행 계획이 있으면 실행
        if planning_state and planning_state.get("execution_steps"):
            logger.info(f"[TeamSupervisor] Routing to execute - {len(planning_state['execution_steps'])} steps found")
            return "execute"

        logger.info("[TeamSupervisor] No execution steps found, routing to respond")
        return "respond"

    async def initialize_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        초기화 노드
        """
        logger.info("[TeamSupervisor] Initializing")

        state["start_time"] = datetime.now()
        state["status"] = "initialized"
        state["current_phase"] = "initialization"
        state["active_teams"] = []
        state["completed_teams"] = []
        state["failed_teams"] = []
        state["team_results"] = {}
        state["error_log"] = []

        return state

    async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        계획 수립 노드
        PlanningAgent를 사용하여 의도 분석 및 실행 계획 생성
        + Long-term Memory 로딩 (RELEVANT 쿼리만)
        """
        logger.info("[TeamSupervisor] Planning phase")

        state["current_phase"] = "planning"

        # WebSocket: Planning 시작 알림
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
        if progress_callback:
            try:
                await progress_callback("planning_start", {
                    "message": "계획을 수립하고 있습니다..."
                })
                logger.debug("[TeamSupervisor] Sent planning_start via WebSocket")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to send planning_start: {e}")

        # 의도 분석
        query = state.get("query", "")
        intent_result = await self.planning_agent.analyze_intent(query)

        # ============================================================================
        # Long-term Memory 로딩 (조기 단계 - RELEVANT 쿼리만)
        # ============================================================================
        user_id = state.get("user_id")
        if user_id and intent_result.intent_type != IntentType.IRRELEVANT:
            try:
                logger.info(f"[TeamSupervisor] Loading Long-term Memory for user {user_id}")
                async for db_session in get_async_db():
                    memory_service = LongTermMemoryService(db_session)

                    # 최근 대화 기록 로드 (RELEVANT만)
                    loaded_memories = await memory_service.load_recent_memories(
                        user_id=user_id,
                        limit=settings.MEMORY_LOAD_LIMIT,
                        relevance_filter="RELEVANT"
                    )

                    # 사용자 선호도 로드
                    user_preferences = await memory_service.get_user_preferences(user_id)

                    state["loaded_memories"] = loaded_memories
                    state["user_preferences"] = user_preferences
                    state["memory_load_time"] = datetime.now().isoformat()

                    logger.info(f"[TeamSupervisor] Loaded {len(loaded_memories)} memories and preferences for user {user_id}")
                    break  # get_db()는 generator이므로 첫 번째 세션만 사용
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to load Long-term Memory: {e}")
                # Memory 로딩 실패해도 계속 진행 (비필수 기능)

        # ⚡ IRRELEVANT/UNCLEAR 조기 종료 - 불필요한 처리 건너뛰기 (3초 → 0.6초 최적화)
        if intent_result.intent_type == IntentType.IRRELEVANT:
            logger.info("⚡ IRRELEVANT detected, early return with minimal state (performance optimization)")
            state["planning_state"] = {
                "analyzed_intent": {
                    "intent_type": "irrelevant",
                    "confidence": intent_result.confidence,
                    "keywords": intent_result.keywords,
                    "entities": intent_result.entities
                },
                "execution_steps": [],
                "raw_query": query,
                "intent_confidence": intent_result.confidence
            }
            state["execution_plan"] = {
                "intent": "irrelevant",
                "strategy": "sequential",
                "steps": []
            }
            state["active_teams"] = []
            return state

        if intent_result.intent_type == IntentType.UNCLEAR and intent_result.confidence < 0.3:
            logger.info(f"⚡ Low-confidence UNCLEAR detected ({intent_result.confidence:.2f}), early return (performance optimization)")
            state["planning_state"] = {
                "analyzed_intent": {
                    "intent_type": "unclear",
                    "confidence": intent_result.confidence,
                    "keywords": intent_result.keywords,
                    "entities": intent_result.entities
                },
                "execution_steps": [],
                "raw_query": query,
                "intent_confidence": intent_result.confidence
            }
            state["execution_plan"] = {
                "intent": "unclear",
                "strategy": "sequential",
                "steps": []
            }
            state["active_teams"] = []
            return state

        # 실행 계획 생성 (정상 쿼리만)
        execution_plan = await self.planning_agent.create_execution_plan(intent_result)

        # Planning State 생성
        planning_state = PlanningState(
            raw_query=query,
            analyzed_intent={
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "keywords": intent_result.keywords,
                "entities": intent_result.entities
            },
            intent_confidence=intent_result.confidence,
            available_agents=AgentRegistry.list_agents(enabled_only=True),
            available_teams=list(self.teams.keys()),
            execution_steps=[
                {
                    # 식별 정보
                    "step_id": f"step_{i}",
                    "step_type": self._get_step_type_for_agent(step.agent_name),
                    "agent_name": step.agent_name,
                    "team": self._get_team_for_agent(step.agent_name),

                    # 작업 정보
                    "task": self._get_task_name_for_agent(step.agent_name, intent_result),
                    "description": self._get_task_description_for_agent(step.agent_name, intent_result),

                    # 상태 추적 (초기값)
                    "status": "pending",
                    "progress_percentage": 0,

                    # 타이밍 (초기값)
                    "started_at": None,
                    "completed_at": None,

                    # 결과 (초기값)
                    "result": None,
                    "error": None
                }
                for i, step in enumerate(execution_plan.steps)
            ],
            execution_strategy=execution_plan.strategy.value,
            parallel_groups=execution_plan.parallel_groups,
            plan_validated=True,
            validation_errors=[],
            estimated_total_time=execution_plan.estimated_time
        )

        state["planning_state"] = planning_state
        state["execution_plan"] = {
            "intent": intent_result.intent_type.value,
            "strategy": execution_plan.strategy.value,
            "steps": planning_state["execution_steps"]
        }

        # 활성화할 팀 결정
        active_teams = set()
        for step in planning_state["execution_steps"]:
            team = step.get("team")
            if team:
                active_teams.add(team)

        state["active_teams"] = list(active_teams)

        logger.info(f"[TeamSupervisor] Plan created: {len(planning_state['execution_steps'])} steps, {len(active_teams)} teams")

        # 디버그: execution_steps 내용 로깅
        for step in planning_state["execution_steps"]:
            logger.debug(f"  Step: agent={step.get('agent_name')}, team={step.get('team')}, status={step.get('status')}")

        if not planning_state["execution_steps"]:
            logger.warning("[TeamSupervisor] WARNING: No execution steps created in planning phase!")

        # WebSocket: 계획 완료 알림
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
        if progress_callback:
            try:
                await progress_callback("plan_ready", {
                    "intent": intent_result.intent_type.value,
                    "confidence": intent_result.confidence,
                    "execution_steps": planning_state["execution_steps"],
                    "execution_strategy": execution_plan.strategy.value,
                    "estimated_total_time": execution_plan.estimated_time,
                    "keywords": intent_result.keywords
                })
                logger.info("[TeamSupervisor] Sent plan_ready via WebSocket")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to send plan_ready: {e}")

        return state

    def _get_team_for_agent(self, agent_name: str) -> str:
        """Agent가 속한 팀 찾기"""
        # 팀 이름 매핑 (agent_selection.txt에서 사용하는 이름들)
        team_name_mapping = {
            "search_team": "search",
            "analysis_team": "analysis",
            "document_team": "document"
        }

        # 이미 팀 이름인 경우 바로 매핑
        if agent_name in team_name_mapping:
            return team_name_mapping[agent_name]

        # Agent 이름인 경우 기존 로직 사용
        from app.service_agent.foundation.agent_adapter import AgentAdapter
        dependencies = AgentAdapter.get_agent_dependencies(agent_name)
        return dependencies.get("team", "search")

    def _get_step_type_for_agent(self, agent_name: str) -> str:
        """
        Agent 이름을 step_type으로 매핑

        Args:
            agent_name: Agent 이름 (예: "search_team", "analysis_team")

        Returns:
            step_type (예: "search", "analysis", "document")
        """
        team = self._get_team_for_agent(agent_name)

        # Team 이름이 곧 step_type
        step_type_mapping = {
            "search": "search",
            "document": "document",
            "analysis": "analysis"
        }

        return step_type_mapping.get(team, "planning")

    def _get_task_name_for_agent(self, agent_name: str, intent_result) -> str:
        """
        Agent별 간단한 작업명 생성

        Args:
            agent_name: Agent 이름
            intent_result: Intent 분석 결과

        Returns:
            간단한 작업명 (예: "정보 검색", "데이터 분석")
        """
        team = self._get_team_for_agent(agent_name)
        intent_type = intent_result.intent_type.value

        # 팀별 기본 작업명
        base_names = {
            "search": "정보 검색",
            "analysis": "데이터 분석",
            "document": "문서 처리"
        }

        base_name = base_names.get(team, "작업 실행")

        # Intent에 따라 구체화
        if intent_type == "legal_consult":
            return f"법률 {base_name}"
        elif intent_type == "market_inquiry":
            return f"시세 {base_name}"
        elif intent_type == "loan_consult":
            return f"대출 {base_name}"
        elif intent_type == "contract_review":
            return f"계약서 {base_name}"
        elif intent_type == "contract_creation":
            return f"계약서 생성"
        else:
            return base_name

    def _get_task_description_for_agent(self, agent_name: str, intent_result) -> str:
        """
        Agent별 상세 설명 생성

        Args:
            agent_name: Agent 이름
            intent_result: Intent 분석 결과

        Returns:
            상세 작업 설명
        """
        team = self._get_team_for_agent(agent_name)
        intent_type = intent_result.intent_type.value
        keywords = intent_result.keywords[:3] if intent_result.keywords else []

        # 팀별 + Intent별 설명 생성
        if team == "search":
            if intent_type == "legal_consult":
                return f"법률 관련 정보 및 판례 검색"
            elif intent_type == "market_inquiry":
                return f"부동산 시세 및 거래 정보 조회"
            elif intent_type == "loan_consult":
                return f"대출 관련 정보 및 금융상품 검색"
            else:
                keyword_text = f" ({', '.join(keywords)})" if keywords else ""
                return f"관련 정보 검색{keyword_text}"

        elif team == "analysis":
            if intent_type == "legal_consult":
                return f"법률 데이터 분석 및 리스크 평가"
            elif intent_type == "market_inquiry":
                return f"시세 데이터 분석 및 시장 동향 파악"
            elif intent_type == "loan_consult":
                return f"대출 조건 분석 및 금리 비교"
            else:
                return f"데이터 분석 및 인사이트 도출"

        elif team == "document":
            if intent_type == "contract_creation":
                return f"계약서 초안 작성"
            elif intent_type == "contract_review":
                return f"계약서 검토 및 리스크 분석"
            else:
                return f"문서 처리 및 생성"

        else:
            return f"{agent_name} 실행"

    def _find_step_id_for_team(
        self,
        team_name: str,
        planning_state: Optional[PlanningState]
    ) -> Optional[str]:
        """
        팀 이름으로 해당하는 step_id 찾기

        Args:
            team_name: 팀 이름 (예: "search", "analysis")
            planning_state: PlanningState

        Returns:
            step_id 또는 None
        """
        if not planning_state:
            return None

        for step in planning_state.get("execution_steps", []):
            if step.get("team") == team_name:
                return step.get("step_id")

        return None

    async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        팀 실행 노드
        계획에 따라 팀들을 실행
        """
        logger.info("[TeamSupervisor] Executing teams")

        state["current_phase"] = "executing"

        # WebSocket: 실행 시작 알림
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
        planning_state = state.get("planning_state")
        if progress_callback and planning_state:
            try:
                analyzed_intent = planning_state.get("analyzed_intent", {})
                await progress_callback("execution_start", {
                    "message": "작업 실행을 시작합니다...",
                    "execution_steps": planning_state.get("execution_steps", []),
                    # Complete ExecutionPlan data for Frontend
                    "intent": analyzed_intent.get("intent_type", "unknown"),
                    "confidence": analyzed_intent.get("confidence", 0.0),
                    "execution_strategy": planning_state.get("execution_strategy", "sequential"),
                    "estimated_total_time": planning_state.get("estimated_total_time", 0),
                    "keywords": analyzed_intent.get("keywords", [])
                })
                logger.info("[TeamSupervisor] Sent execution_start via WebSocket")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to send execution_start: {e}")

        execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
        active_teams = state.get("active_teams", [])

        # 공유 상태 생성
        shared_state = StateManager.create_shared_state(
            query=state["query"],
            session_id=state["session_id"]
        )

        # 팀별 실행
        if execution_strategy == "parallel" and len(active_teams) > 1:
            # 병렬 실행
            results = await self._execute_teams_parallel(active_teams, shared_state, state)
        else:
            # 순차 실행
            results = await self._execute_teams_sequential(active_teams, shared_state, state)

        # 결과 저장
        for team_name, team_result in results.items():
            state = StateManager.merge_team_results(state, team_name, team_result)

        return state

    async def _execute_teams_parallel(
        self,
        teams: List[str],
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Dict[str, Any]:
        """팀 병렬 실행"""
        logger.info(f"[TeamSupervisor] Executing {len(teams)} teams in parallel")

        tasks = []
        for team_name in teams:
            if team_name in self.teams:
                task = self._execute_single_team(team_name, shared_state, main_state)
                tasks.append((team_name, task))

        results = {}
        for team_name, task in tasks:
            try:
                result = await task
                results[team_name] = result
                logger.info(f"[TeamSupervisor] Team '{team_name}' completed")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")
                results[team_name] = {"status": "failed", "error": str(e)}

        return results

    async def _execute_teams_sequential(
        self,
        teams: List[str],
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Dict[str, Any]:
        """팀 순차 실행 + execution_steps status 업데이트"""
        logger.info(f"[TeamSupervisor] Executing {len(teams)} teams sequentially")

        results = {}
        planning_state = main_state.get("planning_state")

        for team_name in teams:
            if team_name in self.teams:
                # Step ID 찾기
                step_id = self._find_step_id_for_team(team_name, planning_state)

                try:
                    # ✅ 실행 전: status = "in_progress"
                    if step_id and planning_state:
                        planning_state = StateManager.update_step_status(
                            planning_state,
                            step_id,
                            "in_progress",
                            progress=0
                        )
                        main_state["planning_state"] = planning_state

                        # WebSocket: TODO 상태 변경 알림 (in_progress)
                        session_id = main_state.get("session_id")
                        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
                        if progress_callback:
                            try:
                                await progress_callback("todo_updated", {
                                    "execution_steps": planning_state["execution_steps"]
                                })
                            except Exception as ws_error:
                                logger.error(f"[TeamSupervisor] Failed to send todo_updated (in_progress): {ws_error}")

                    # 팀 실행
                    result = await self._execute_single_team(team_name, shared_state, main_state)
                    results[team_name] = result

                    # ✅ 실행 성공: status = "completed"
                    if step_id and planning_state:
                        planning_state = StateManager.update_step_status(
                            planning_state,
                            step_id,
                            "completed",
                            progress=100
                        )
                        # 결과 저장
                        for step in planning_state["execution_steps"]:
                            if step["step_id"] == step_id:
                                step["result"] = result
                                break
                        main_state["planning_state"] = planning_state

                        # WebSocket: TODO 상태 변경 알림 (completed)
                        session_id = main_state.get("session_id")
                        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
                        if progress_callback:
                            try:
                                await progress_callback("todo_updated", {
                                    "execution_steps": planning_state["execution_steps"]
                                })
                            except Exception as ws_error:
                                logger.error(f"[TeamSupervisor] Failed to send todo_updated (completed): {ws_error}")

                    logger.info(f"[TeamSupervisor] Team '{team_name}' completed")

                    # 데이터 전달 (다음 팀을 위해)
                    if team_name == "search" and "analysis" in teams:
                        # SearchTeam 결과를 AnalysisTeam에 전달
                        main_state["team_results"][team_name] = self._extract_team_data(result, team_name)

                except Exception as e:
                    # ✅ 실행 실패: status = "failed"
                    logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")

                    if step_id and planning_state:
                        planning_state = StateManager.update_step_status(
                            planning_state,
                            step_id,
                            "failed",
                            error=str(e)
                        )
                        main_state["planning_state"] = planning_state

                        # WebSocket: TODO 상태 변경 알림 (failed)
                        session_id = main_state.get("session_id")
                        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
                        if progress_callback:
                            try:
                                await progress_callback("todo_updated", {
                                    "execution_steps": planning_state["execution_steps"]
                                })
                            except Exception as ws_error:
                                logger.error(f"[TeamSupervisor] Failed to send todo_updated (failed): {ws_error}")

                    results[team_name] = {"status": "failed", "error": str(e)}

        return results

    async def _execute_single_team(
        self,
        team_name: str,
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Any:
        """단일 팀 실행"""
        team = self.teams[team_name]

        if team_name == "search":
            return await team.execute(shared_state)

        elif team_name == "document":
            # 문서 타입 추출
            doc_type = self._extract_document_type(main_state)
            return await team.execute(
                shared_state,
                document_type=doc_type
            )

        elif team_name == "analysis":
            # 이전 팀 결과 전달
            input_data = main_state.get("team_results", {})
            return await team.execute(
                shared_state,
                analysis_type="comprehensive",
                input_data=input_data
            )

        return {"status": "skipped"}

    def _extract_document_type(self, state: MainSupervisorState) -> str:
        """문서 타입 추출"""
        intent = state.get("planning_state", {}).get("analyzed_intent", {})
        intent_type = intent.get("intent_type", "")

        if "계약서" in intent_type or "작성" in intent_type:
            return "lease_contract"
        elif "매매" in intent_type:
            return "sales_contract"
        else:
            return "lease_contract"

    def _extract_team_data(self, team_state: Any, team_name: str) -> Dict:
        """팀 결과에서 데이터 추출"""
        if team_name == "search":
            return {
                "legal_search": team_state.get("legal_results", []),
                "real_estate_search": team_state.get("real_estate_results", []),
                "loan_search": team_state.get("loan_results", [])
            }
        elif team_name == "document":
            return {
                "document": team_state.get("final_document", ""),
                "review": team_state.get("review_result", {})
            }
        elif team_name == "analysis":
            return {
                "report": team_state.get("report", {}),
                "insights": team_state.get("insights", [])
            }
        return {}

    async def aggregate_results_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        결과 집계 노드
        """
        logger.info("[TeamSupervisor] === Aggregating results ===")

        state["current_phase"] = "aggregation"

        # 팀 결과 집계
        aggregated = {}
        team_results = state.get("team_results", {})
        logger.info(f"[TeamSupervisor] Team results to aggregate: {list(team_results.keys())}")

        for team_name, team_data in team_results.items():
            if team_data:
                aggregated[team_name] = {
                    "status": "success",
                    "data": team_data
                }
                logger.info(f"[TeamSupervisor] Aggregated {team_name}: {len(str(team_data))} bytes")

        state["aggregated_results"] = aggregated

        # 실행 통계
        total_teams = len(state.get("active_teams", []))
        completed_teams = len(state.get("completed_teams", []))
        failed_teams = len(state.get("failed_teams", []))

        logger.info(f"[TeamSupervisor] === Aggregation complete: {completed_teams}/{total_teams} teams succeeded, {failed_teams} failed ===")
        return state

    async def generate_response_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        응답 생성 노드
        """
        logger.info("[TeamSupervisor] === Generating response ===")

        state["current_phase"] = "response_generation"

        # 기능 외 질문 체크
        planning_state = state.get("planning_state", {})
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")
        confidence = analyzed_intent.get("confidence", 0.0)

        logger.info(f"[TeamSupervisor] Intent type: {intent_type}, confidence: {confidence:.2f}")

        # IRRELEVANT 또는 낮은 confidence UNCLEAR는 안내 메시지 반환
        if intent_type == "irrelevant" or (intent_type == "unclear" and confidence < 0.3):
            logger.info(f"[TeamSupervisor] Generating guidance response for {intent_type}")
            response = self._generate_out_of_scope_response(state)
        else:
            # 정상적인 응답 생성
            aggregated_results = state.get("aggregated_results", {})
            logger.info(f"[TeamSupervisor] Aggregated results available: {list(aggregated_results.keys())}")

            if self.planning_agent.llm_service:
                logger.info("[TeamSupervisor] Using LLM for response generation")
                response = await self._generate_llm_response(state)
            else:
                logger.info("[TeamSupervisor] Using simple response generation (no LLM)")
                response = self._generate_simple_response(state)

        logger.info(f"[TeamSupervisor] Response type: {response.get('type', 'unknown')}")
        state["final_response"] = response
        state["status"] = "completed"

        # 실행 시간 계산
        if state.get("start_time"):
            state["end_time"] = datetime.now()
            state["total_execution_time"] = (state["end_time"] - state["start_time"]).total_seconds()
            logger.info(f"[TeamSupervisor] Total execution time: {state['total_execution_time']:.2f}s")

        # ============================================================================
        # Long-term Memory 저장 (RELEVANT 쿼리만)
        # ============================================================================
        user_id = state.get("user_id")
        if user_id and intent_type not in ["irrelevant", "unclear"]:
            try:
                logger.info(f"[TeamSupervisor] Saving conversation to Long-term Memory for user {user_id}")

                async for db_session in get_async_db():
                    memory_service = LongTermMemoryService(db_session)

                    # 응답 요약 생성 (최대 200자)
                    response_summary = response.get("summary", "")
                    if not response_summary and response.get("answer"):
                        response_summary = response.get("answer", "")[:200]
                    if not response_summary:
                        response_summary = f"{response.get('type', 'response')} 생성 완료"

                    # chat_session_id 추출 (Chat History & State Endpoints)
                    chat_session_id = state.get("chat_session_id")

                    # 대화 저장
                    await memory_service.save_conversation(
                        user_id=user_id,
                        query=state.get("query", ""),
                        response_summary=response_summary,
                        relevance="RELEVANT",
                        session_id=chat_session_id,
                        intent_detected=intent_type,
                        entities_mentioned=analyzed_intent.get("entities", {}),
                        conversation_metadata={
                            "teams_used": state.get("active_teams", []),
                            "response_time": state.get("total_execution_time"),
                            "confidence": confidence
                        }
                    )

                    logger.info(f"[TeamSupervisor] Conversation saved to Long-term Memory")
                    break  # get_db()는 generator이므로 첫 번째 세션만 사용
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to save Long-term Memory: {e}")
                # Memory 저장 실패해도 사용자 응답에는 영향 없음 (비필수 기능)

        logger.info("[TeamSupervisor] === Response generation complete ===")
        return state

    def _safe_json_dumps(self, obj: Any) -> str:
        """Safely convert object to JSON string, handling datetime objects"""
        from datetime import datetime

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)

    async def _generate_llm_response(self, state: MainSupervisorState) -> Dict:
        """
        LLM을 사용한 응답 생성
        LLMService의 generate_final_response 메서드를 사용하여 중앙화된 응답 생성
        """
        query = state.get("query", "")
        aggregated = state.get("aggregated_results", {})
        intent_info = state.get("planning_state", {}).get("analyzed_intent", {})

        try:
            # LLMService의 generate_final_response 메서드 호출
            response = await self.planning_agent.llm_service.generate_final_response(
                query=query,
                aggregated_results=aggregated,
                intent_info=intent_info
            )

            return response

        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return self._generate_simple_response(state)

    def _generate_simple_response(self, state: MainSupervisorState) -> Dict:
        """간단한 응답 생성"""
        aggregated = state.get("aggregated_results", {})

        summary_parts = []
        for team_name, team_data in aggregated.items():
            if team_data.get("status") == "success":
                summary_parts.append(f"{team_name} 팀 완료")

        return {
            "type": "summary",
            "summary": ", ".join(summary_parts) if summary_parts else "처리 완료",
            "teams_used": list(aggregated.keys()),
            "data": aggregated
        }

    def _generate_out_of_scope_response(self, state: MainSupervisorState) -> Dict:
        """기능 외 질문에 대한 안내 응답 생성"""
        planning_state = state.get("planning_state", {})
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")
        query = state.get("query", "")

        # Intent 타입에 따른 메시지
        if intent_type == "irrelevant":
            message = """안녕하세요! 저는 부동산 전문 상담 AI입니다.

현재 질문은 부동산과 관련이 없는 것으로 보입니다.

**제가 도와드릴 수 있는 분야:**
- 전세/월세/매매 관련 법률 상담
- 부동산 시세 조회 및 시장 분석
- 주택담보대출 및 전세자금대출 상담
- 임대차 계약서 작성 및 검토
- 부동산 투자 리스크 분석

부동산과 관련된 질문을 해주시면 자세히 안내해드리겠습니다."""

        elif intent_type == "unclear":
            message = f"""질문의 의도를 명확히 파악하기 어렵습니다.

**더 구체적으로 질문해주시면 도움이 됩니다:**
- 어떤 상황인지 구체적으로 설명해주세요
- 무엇을 알고 싶으신지 명확히 해주세요
- 관련된 정보(지역, 금액, 계약 조건 등)를 포함해주세요

**예시:**
- "강남구 아파트 전세 시세 알려주세요"
- "전세금 5% 인상이 가능한가요?"
- "임대차 계약서 검토해주세요"

다시 한번 질문을 구체적으로 말씀해주시면 정확히 답변드리겠습니다."""

        else:
            message = "질문을 이해하는데 어려움이 있습니다. 부동산 관련 질문을 명확히 해주시면 도움을 드리겠습니다."

        return {
            "type": "guidance",
            "message": message,
            "original_query": query,
            "detected_intent": intent_type,
            "teams_used": [],
            "data": {}
        }

    async def _ensure_checkpointer(self):
        """Checkpointer 초기화 및 graph 재컴파일 (최초 1회만)"""
        if not self.enable_checkpointing:
            return

        if not self._checkpointer_initialized:
            try:
                logger.info("Initializing AsyncPostgresSaver checkpointer with PostgreSQL...")

                # Use AsyncPostgresSaver for PostgreSQL
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                from app.core.config import settings

                # PostgreSQL 연결 문자열 (중앙화된 설정 사용)
                DB_URI = settings.postgres_url
                logger.info(f"Using PostgreSQL URL from centralized config: {DB_URI.replace(settings.POSTGRES_PASSWORD, '***')}")

                # Create and enter async context manager
                self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
                self.checkpointer = await self._checkpoint_cm.__aenter__()

                # 최초 테이블 생성 (checkpoints, checkpoint_blobs, checkpoint_writes)
                await self.checkpointer.setup()

                self._checkpointer_initialized = True

                # Checkpointer와 함께 graph 재컴파일
                logger.info("Recompiling graph with checkpointer...")
                self._build_graph_with_checkpointer()

                logger.info("✅ PostgreSQL checkpointer initialized and graph recompiled successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
                self.enable_checkpointing = False

    def _build_graph_with_checkpointer(self):
        """Checkpointer와 함께 workflow graph 재구성"""
        workflow = StateGraph(MainSupervisorState)

        # 노드 추가 (기존과 동일)
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute_teams", self.execute_teams_node)
        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 구성 (기존과 동일)
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "planning")

        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "execute": "execute_teams",
                "respond": "generate_response"
            }
        )

        workflow.add_edge("execute_teams", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # Checkpointer와 함께 compile
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Team-based workflow graph built with checkpointer")

    async def process_query_streaming(
        self,
        query: str,
        session_id: str = "default",
        chat_session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        실시간 스트리밍 쿼리 처리 메인 메서드 (WebSocket 전용)

        Args:
            query: 사용자 쿼리
            session_id: 세션 ID (HTTP/WebSocket)
            chat_session_id: 채팅 세션 ID (Chat History & State Endpoints, optional)
            user_id: 사용자 ID (Long-term Memory용, 없으면 None)
            progress_callback: 진행 상황 콜백 함수 (WebSocket 전송용)
                               async def callback(event_type: str, event_data: dict)

        Returns:
            처리 결과
        """
        logger.info(f"[TeamSupervisor] Processing query (streaming): {query[:100]}...")
        if user_id:
            logger.info(f"[TeamSupervisor] User ID: {user_id} (Long-term Memory enabled)")
        if chat_session_id:
            logger.info(f"[TeamSupervisor] Chat session ID: {chat_session_id} (Chat History & State Endpoints)")

        # Checkpointer 초기화 (최초 1회)
        await self._ensure_checkpointer()

        # Progress Callback 별도 저장 (State와 분리)
        if progress_callback:
            self._progress_callbacks[session_id] = progress_callback
            logger.debug(f"[TeamSupervisor] Progress callback registered for session: {session_id}")

        # 초기 상태 생성 (Callback은 State에 포함하지 않음)
        initial_state = MainSupervisorState(
            query=query,
            session_id=session_id,
            chat_session_id=chat_session_id,  # Chat History & State Endpoints ID
            request_id=f"req_{datetime.now().timestamp()}",
            user_id=user_id,  # Long-term Memory용
            planning_state=None,
            execution_plan=None,
            search_team_state=None,
            document_team_state=None,
            analysis_team_state=None,
            current_phase="",
            active_teams=[],
            completed_teams=[],
            failed_teams=[],
            team_results={},
            aggregated_results={},
            final_response=None,
            start_time=datetime.now(),
            end_time=None,
            total_execution_time=None,
            error_log=[],
            status="initialized",
            # Long-term Memory 필드 (초기화)
            loaded_memories=None,
            user_preferences=None,
            memory_load_time=None
        )

        # 워크플로우 실행
        try:
            # Checkpointing이 활성화되어 있으면 config에 thread_id 전달
            if self.checkpointer:
                # ✅ chat_session_id를 thread_id로 사용 (Chat History & State Endpoints)
                # chat_session_id가 없으면 session_id (HTTP) 사용 (하위 호환성)
                thread_id = chat_session_id if chat_session_id else session_id

                config = {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
                logger.info(f"Running with checkpointer (thread_id: {thread_id}, type: {'chat' if chat_session_id else 'http'})")
                final_state = await self.app.ainvoke(initial_state, config=config)
            else:
                logger.info("Running without checkpointer")
                final_state = await self.app.ainvoke(initial_state)

            # Callback 정리 (메모리 관리)
            if session_id in self._progress_callbacks:
                del self._progress_callbacks[session_id]
                logger.debug(f"[TeamSupervisor] Progress callback cleaned up for session: {session_id}")

            return final_state
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)

            # 에러 발생 시에도 callback으로 전송
            callback = self._progress_callbacks.get(session_id)
            if callback:
                try:
                    await callback("error", {
                        "error": str(e),
                        "message": "처리 중 오류가 발생했습니다."
                    })
                except:
                    pass

            # Callback 정리
            if session_id in self._progress_callbacks:
                del self._progress_callbacks[session_id]

            return {
                "status": "error",
                "error": str(e),
                "final_response": {
                    "type": "error",
                    "message": "처리 중 오류가 발생했습니다.",
                    "error": str(e)
                }
            }

    async def cleanup(self):
        """
        Cleanup resources, especially the checkpointer context manager
        Call this when done using the supervisor
        """
        if self._checkpoint_cm is not None:
            try:
                await self._checkpoint_cm.__aexit__(None, None, None)
                logger.info("Checkpointer context manager closed successfully")
            except Exception as e:
                logger.error(f"Error closing checkpointer: {e}")
            finally:
                self._checkpoint_cm = None
                self.checkpointer = None
                self._checkpointer_initialized = False


# 테스트 코드
if __name__ == "__main__":
    async def test_team_supervisor():
        # TeamBasedSupervisor 초기화
        supervisor = TeamBasedSupervisor()

        # 테스트 쿼리
        test_queries = [
            "전세금 5% 인상 가능한가요?",
            "강남구 아파트 시세와 투자 분석해주세요",
            "임대차계약서 작성하고 검토해주세요"
        ]

        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print("-"*80)

            result = await supervisor.process_query(query, "test_team_supervisor")

            print(f"Status: {result.get('status')}")
            print(f"Phase: {result.get('current_phase')}")
            print(f"Teams used: {result.get('active_teams', [])}")

            if result.get("final_response"):
                response = result["final_response"]
                print(f"\nResponse type: {response.get('type')}")
                if response.get("answer"):
                    print(f"Answer: {response.get('answer', '')[:200]}...")
                elif response.get("summary"):
                    print(f"Summary: {response.get('summary')}")

            if result.get("total_execution_time"):
                print(f"\nExecution time: {result['total_execution_time']:.2f}s")

    import asyncio
    asyncio.run(test_team_supervisor())