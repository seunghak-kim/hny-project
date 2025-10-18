"""
Separated State Definitions for Team-based Architecture
각 팀별로 독립적인 State를 정의하여 State pollution을 방지

Refactored for better organization and maintainability
- Added logging support
- Improved error handling
- Better type hints
- Added standard result format for Phase 2
- Added TodoItem for Progress Flow WebSocket integration
"""

import logging
from typing import TypedDict, Dict, List, Any, Optional, Literal, Union, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

# Configure logger
logger = logging.getLogger(__name__)

# ============================================================================
# STANDARD RESULT FORMAT (Phase 2 Preparation)
# ============================================================================

@dataclass
class StandardResult:
    """
    모든 Agent의 표준 응답 포맷
    Phase 2에서 본격 활용 예정
    """
    agent_name: str
    status: Literal["success", "failure", "partial"]
    data: Dict[str, Any]
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for State storage"""
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================================================
# SHARED STATE DEFINITIONS
# ============================================================================

class SearchKeywords(TypedDict):
    """검색 키워드 구조"""
    legal: List[str]
    real_estate: List[str]
    loan: List[str]
    general: List[str]


class SharedState(TypedDict):
    """
    모든 팀이 공유하는 최소한의 상태
    - 필수 필드만 포함
    - 팀 간 통신의 기본 단위
    """
    user_query: str
    session_id: str
    user_id: Optional[int]  # 사용자 ID (로그인 시, 없으면 None)
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]

# ============================================================================
# TEAM-SPECIFIC STATE DEFINITIONS
# ============================================================================

class SearchTeamState(TypedDict):
    """검색 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Search specific
    keywords: Optional[SearchKeywords]
    search_scope: List[str]  # ["legal", "real_estate", "loan"]
    filters: Dict[str, Any]

    # Search results
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]
    loan_results: List[Dict[str, Any]]
    property_search_results: List[Dict[str, Any]]  # 개별 매물 검색 결과 (RealEstateSearchTool)
    aggregated_results: Dict[str, Any]

    # Metadata
    total_results: int
    search_time: float
    sources_used: List[str]
    search_progress: Dict[str, str]

    # Execution tracking
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    current_search: Optional[str]
    execution_strategy: Optional[str]


class DocumentTemplate(TypedDict):
    """문서 템플릿 구조"""
    template_id: str
    template_name: str
    template_content: str
    placeholders: List[str]


class DocumentContent(TypedDict):
    """문서 내용 구조"""
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: str


class ReviewResult(TypedDict):
    """검토 결과 구조"""
    reviewed: bool
    risk_level: str  # "low", "medium", "high"
    risks: List[Dict[str, Any]]
    recommendations: List[str]
    compliance_check: Dict[str, bool]


class DocumentTeamState(TypedDict):
    """문서 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Document specific
    document_type: str  # "lease_contract", "sales_contract", etc.
    template: Optional[DocumentTemplate]
    document_content: Optional[DocumentContent]
    generation_progress: Dict[str, str]

    # Review specific
    review_needed: bool
    review_result: Optional[ReviewResult]
    final_document: Optional[str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    generation_time: Optional[float]
    review_time: Optional[float]

    # Error tracking
    error: Optional[str]


class AnalysisInput(TypedDict):
    """분석 입력 구조"""
    data_source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class AnalysisMetrics(TypedDict):
    """분석 지표 구조"""
    avg_price: Optional[float]
    max_price: Optional[float]
    min_price: Optional[float]
    price_trend: Optional[str]
    risk_score: Optional[float]
    investment_score: Optional[float]


class AnalysisInsight(TypedDict):
    """분석 인사이트 구조"""
    insight_type: str
    content: str
    confidence: float
    supporting_data: Dict[str, Any]


class AnalysisReport(TypedDict):
    """분석 보고서 구조"""
    title: str
    summary: str
    sections: List[Dict[str, Any]]
    metrics: AnalysisMetrics
    insights: List[AnalysisInsight]
    recommendations: List[str]


class AnalysisTeamState(TypedDict):
    """분석 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Analysis specific
    analysis_type: str  # "market", "risk", "comprehensive", etc.
    input_data: Dict[str, Any]

    # Analysis results
    raw_analysis: Dict[str, Any]  # Raw analysis results from analysis_tools
    metrics: Dict[str, float]
    insights: List[str]
    report: Dict[str, Any]
    visualization_data: Optional[Dict[str, Any]]
    recommendations: List[str]
    confidence_score: float

    # Progress tracking
    analysis_progress: Dict[str, str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    analysis_time: Optional[float]

    # Error tracking
    error: Optional[str]

# ============================================================================
# SUPERVISOR STATE DEFINITIONS
# ============================================================================

class ExecutionStepState(TypedDict):
    """
    execution_steps의 표준 형식 - TODO 아이템 + ProcessFlow 호환

    간소화된 TODO 관리: 실시간 WebSocket 업데이트용
    - Planning Agent가 생성
    - StateManager가 상태 업데이트
    - WebSocket으로 Frontend에 전송
    """
    # 식별 정보 (4개)
    step_id: str                    # 고유 ID (예: "step_0", "step_1")
    step_type: str                  # 'planning'|'search'|'document'|'analysis'|'synthesis'|'generation'
    agent_name: str                 # 담당 에이전트 (예: "search_team")
    team: str                       # 담당 팀 (예: "search")

    # 작업 정보 (2개)
    task: str                       # 간단한 작업명 (예: "법률 정보 검색")
    description: str                # 상세 설명 (사용자에게 표시)

    # 상태 추적 (2개)
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    progress_percentage: int        # 진행률 0-100

    # 타이밍 (2개)
    started_at: Optional[str]       # 시작 시간 (ISO format datetime)
    completed_at: Optional[str]     # 완료 시간 (ISO format datetime)

    # 결과/에러 (2개)
    result: Optional[Dict[str, Any]]  # 실행 결과 데이터
    error: Optional[str]              # 에러 메시지


class PlanningState(TypedDict):
    """계획 수립 전용 State"""
    raw_query: str
    analyzed_intent: Dict[str, Any]
    intent_confidence: float
    available_agents: List[str]
    available_teams: List[str]
    execution_steps: List[ExecutionStepState]  # ✅ 타입 표준화: Dict → ExecutionStepState
    execution_strategy: str
    parallel_groups: Optional[List[List[str]]]
    plan_validated: bool
    validation_errors: List[str]
    estimated_total_time: float


class MainSupervisorState(TypedDict, total=False):
    """
    메인 Supervisor의 State
    total=False로 설정하여 모든 필드를 선택적으로 만듦
    """
    # Core fields (required)
    query: str
    session_id: str
    chat_session_id: Optional[str]  # Chat History & State Endpoints (conversation_memories.session_id와 매핑)
    request_id: str

    # Planning
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]

    # Team states
    search_team_state: Optional[Dict[str, Any]]
    document_team_state: Optional[Dict[str, Any]]
    analysis_team_state: Optional[Dict[str, Any]]

    # Execution tracking
    current_phase: str
    active_teams: List[str]
    completed_teams: List[str]
    failed_teams: List[str]

    # Results
    team_results: Dict[str, Any]
    aggregated_results: Dict[str, Any]
    final_response: Optional[Dict[str, Any]]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    total_execution_time: Optional[float]

    # Error handling
    error_log: List[str]
    status: str

    # ============================================================================
    # Long-term Memory Fields
    # ============================================================================
    user_id: Optional[int]  # 사용자 ID (로그인 시)
    loaded_memories: Optional[List[Dict[str, Any]]]  # 로드된 대화 기록
    user_preferences: Optional[Dict[str, Any]]  # 사용자 선호도
    memory_load_time: Optional[str]  # Memory 로드 시간 (ISO format)

    # ============================================================================
    # Progress Flow - WebSocket Real-time Integration
    # ============================================================================
    #
    # ⚠️ _progress_callback은 State에 포함되지 않습니다
    #
    # 이유: LangGraph Checkpoint가 State를 직렬화할 때 Callable 타입은
    #       msgpack으로 직렬화할 수 없어 "Type is not msgpack serializable: function" 에러 발생
    #
    # 해결: TeamBasedSupervisor 인스턴스에서 별도 관리
    #       - self._progress_callbacks: Dict[session_id, callback]
    #       - 각 노드에서 self._progress_callbacks.get(session_id)로 접근
    #
    # TODO 관리: PlanningState.execution_steps에서 처리

# ============================================================================
# STATE MANAGEMENT UTILITIES
# ============================================================================

class StateManager:
    """
    State 변환 및 관리 유틸리티
    - Logging 추가
    - Error handling 개선
    - TODO + ProcessFlow 상태 관리
    """

    @staticmethod
    def update_step_status(
        planning_state: PlanningState,
        step_id: str,
        new_status: Literal["pending", "in_progress", "completed", "failed", "skipped", "cancelled"],
        progress: Optional[int] = None,
        error: Optional[str] = None
    ) -> PlanningState:
        """
        개별 execution_step의 상태 업데이트
        TODO 관리 + ProcessFlow 업데이트 공통 사용

        Args:
            planning_state: Planning State
            step_id: 업데이트할 step ID
            new_status: 새로운 상태
            progress: 진행률 (0-100)
            error: 에러 메시지 (실패 시)

        Returns:
            업데이트된 planning_state
        """
        for step in planning_state["execution_steps"]:
            if step["step_id"] == step_id:
                old_status = step["status"]
                step["status"] = new_status

                # 진행률 업데이트
                if progress is not None:
                    step["progress_percentage"] = progress

                # 시작 시간 기록
                if new_status == "in_progress" and not step.get("started_at"):
                    step["started_at"] = datetime.now().isoformat()

                # 완료 시간 기록 + 실행 시간 계산
                if new_status in ["completed", "failed", "skipped", "cancelled"]:
                    step["completed_at"] = datetime.now().isoformat()
                    if step.get("started_at"):
                        try:
                            start = datetime.fromisoformat(step["started_at"])
                            delta = datetime.now() - start
                            step["execution_time_ms"] = int(delta.total_seconds() * 1000)
                        except Exception as e:
                            logger.warning(f"Failed to calculate execution time for step {step_id}: {e}")

                # 에러 기록
                if error:
                    step["error"] = error

                logger.info(f"Step {step_id} status: {old_status} -> {new_status}")
                break

        return planning_state

    @staticmethod
    def create_shared_state(
        query: str,
        session_id: str,
        user_id: Optional[int] = None,
        language: str = "ko",
        timestamp: Optional[str] = None
    ) -> SharedState:
        """공유 State 생성"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        logger.info(f"Creating shared state for session: {session_id}")

        return SharedState(
            user_query=query,
            session_id=session_id,
            user_id=user_id,
            timestamp=timestamp,
            language=language,
            status="pending",
            error_message=None
        )

    @staticmethod
    def extract_shared_state(state: Dict[str, Any]) -> SharedState:
        """전체 State에서 공유 State만 추출"""
        logger.debug(f"Extracting shared state from full state")

        return SharedState(
            user_query=state.get("user_query", ""),
            session_id=state.get("session_id", ""),
            user_id=state.get("user_id"),
            timestamp=state.get("timestamp", datetime.now().isoformat()),
            language=state.get("language", "ko"),
            status=state.get("status", "pending"),
            error_message=state.get("error_message")
        )

    @staticmethod
    def merge_team_results(
        main_state: MainSupervisorState,
        team_name: str,
        team_result: Dict[str, Any]
    ) -> MainSupervisorState:
        """
        팀 결과를 메인 State에 병합
        - Improved error handling
        - Better logging
        """
        logger.info(f"Merging results from team: {team_name}")

        try:
            # Store team result
            if "team_results" not in main_state:
                main_state["team_results"] = {}
            main_state["team_results"][team_name] = team_result

            # Update completed/failed teams
            if team_result.get("status") in ["completed", "success"]:
                if "completed_teams" not in main_state:
                    main_state["completed_teams"] = []
                if team_name not in main_state["completed_teams"]:
                    main_state["completed_teams"].append(team_name)
                    logger.info(f"Team {team_name} completed successfully")
            else:
                if "failed_teams" not in main_state:
                    main_state["failed_teams"] = []
                if team_name not in main_state["failed_teams"]:
                    main_state["failed_teams"].append(team_name)
                    logger.warning(f"Team {team_name} failed")

            # Remove from active teams
            if "active_teams" in main_state and team_name in main_state["active_teams"]:
                main_state["active_teams"].remove(team_name)

        except Exception as e:
            logger.error(f"Error merging team results for {team_name}: {str(e)}")
            if "error_log" not in main_state:
                main_state["error_log"] = []
            main_state["error_log"].append(f"Failed to merge {team_name} results: {str(e)}")

        return main_state

    @staticmethod
    def create_initial_team_state(
        team_type: str,
        shared_state: SharedState,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        팀별 초기 State 생성
        - Improved initialization
        - Better defaults
        """
        logger.info(f"Creating initial state for team: {team_type}")

        # Base shared fields
        base_fields = {
            "team_name": team_type,
            "status": "initialized",
            "shared_context": dict(shared_state),
            "start_time": None,
            "end_time": None,
            "error": None
        }

        try:
            if team_type == "search":
                state = {
                    **base_fields,
                    "keywords": None,
                    "search_scope": ["legal", "real_estate", "loan"],
                    "filters": {},
                    "legal_results": [],
                    "real_estate_results": [],
                    "loan_results": [],
                    "property_search_results": [],  # 개별 매물 검색 결과
                    "aggregated_results": {},
                    "total_results": 0,
                    "search_time": 0.0,
                    "sources_used": [],
                    "search_progress": {},
                    "current_search": None,
                    "execution_strategy": None
                }

            elif team_type == "document":
                doc_type = additional_data.get("document_type", "contract") if additional_data else "contract"
                state = {
                    **base_fields,
                    "document_type": doc_type,
                    "template": None,
                    "document_content": None,
                    "generation_progress": {},
                    "review_needed": True,
                    "review_result": None,
                    "final_document": None,
                    "generation_time": None,
                    "review_time": None
                }

            elif team_type == "analysis":
                analysis_type = additional_data.get("analysis_type", "comprehensive") if additional_data else "comprehensive"
                state = {
                    **base_fields,
                    "analysis_type": analysis_type,
                    "input_data": {},
                    "metrics": {},
                    "insights": [],
                    "report": {},
                    "visualization_data": None,
                    "recommendations": [],
                    "confidence_score": 0.0,
                    "analysis_progress": {},
                    "analysis_time": None
                }

            else:
                raise ValueError(f"Unknown team type: {team_type}")

            # Add any additional data
            if additional_data:
                state.update(additional_data)
                logger.debug(f"Added additional data to {team_type} state")

            return state

        except Exception as e:
            logger.error(f"Error creating initial state for {team_type}: {str(e)}")
            raise

# ============================================================================
# STATE VALIDATION
# ============================================================================

class StateValidator:
    """
    State 유효성 검증
    - Improved error messages
    - Better logging
    """

    @staticmethod
    def validate_shared_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """공유 State 검증"""
        errors = []

        # Required fields
        required_fields = ["user_query", "session_id"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"{field} is required")

        # Status validation
        valid_statuses = ["pending", "processing", "completed", "error"]
        if state.get("status") and state["status"] not in valid_statuses:
            errors.append(f"Invalid status: {state['status']}")

        if errors:
            logger.warning(f"Shared state validation errors: {errors}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_search_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """검색 팀 State 검증"""
        errors = []

        # Check shared state first
        is_valid, shared_errors = StateValidator.validate_shared_state(state.get("shared_context", {}))
        errors.extend(shared_errors)

        # Search specific validation
        search_scope = state.get("search_scope", [])
        valid_scopes = ["legal", "real_estate", "loan"]
        for scope in search_scope:
            if scope not in valid_scopes:
                errors.append(f"Invalid search scope: {scope}")

        if errors:
            logger.warning(f"Search state validation errors: {errors}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_document_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """문서 팀 State 검증"""
        errors = []

        # Check shared state first
        is_valid, shared_errors = StateValidator.validate_shared_state(state.get("shared_context", {}))
        errors.extend(shared_errors)

        # Document specific validation
        if not state.get("document_type"):
            errors.append("document_type is required")

        valid_types = ["contract", "agreement", "report", "notice", "application", "lease_contract", "sales_contract"]
        if state.get("document_type") and state["document_type"] not in valid_types:
            errors.append(f"Invalid document type: {state.get('document_type')}")

        if errors:
            logger.warning(f"Document state validation errors: {errors}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_analysis_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """분석 팀 State 검증"""
        errors = []

        # Check shared state first
        is_valid, shared_errors = StateValidator.validate_shared_state(state.get("shared_context", {}))
        errors.extend(shared_errors)

        # Analysis specific validation
        if not state.get("analysis_type"):
            errors.append("analysis_type is required")

        valid_types = ["market", "risk", "comprehensive", "comparison", "trend"]
        if state.get("analysis_type") and state["analysis_type"] not in valid_types:
            errors.append(f"Invalid analysis type: {state.get('analysis_type')}")

        if errors:
            logger.warning(f"Analysis state validation errors: {errors}")

        return len(errors) == 0, errors

# ============================================================================
# STATE TRANSITION HELPERS (New for Phase 1)
# ============================================================================

class StateTransition:
    """
    State 전환 관리
    - Phase transition logging
    - Error recovery helpers
    """

    @staticmethod
    def update_status(state: Dict[str, Any], new_status: str) -> Dict[str, Any]:
        """Update status with logging"""
        old_status = state.get("status", "unknown")
        state["status"] = new_status
        logger.info(f"Status transition: {old_status} -> {new_status}")
        return state

    @staticmethod
    def record_error(state: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Record error in state"""
        state["error"] = error
        state["status"] = "error"
        if "error_log" not in state:
            state["error_log"] = []
        state["error_log"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        logger.error(f"Error recorded: {error}")
        return state

    @staticmethod
    def mark_completed(state: Dict[str, Any], result: Any = None) -> Dict[str, Any]:
        """Mark task as completed"""
        state["status"] = "completed"
        state["end_time"] = datetime.now()
        if result is not None:
            state["result"] = result

        # Calculate execution time if start_time exists
        if state.get("start_time"):
            delta = state["end_time"] - state["start_time"]
            state["execution_time"] = delta.total_seconds()
            logger.info(f"Task completed in {state['execution_time']:.2f} seconds")

        return state

# ============================================================================
# EXPORT ALL PUBLIC CLASSES
# ============================================================================

__all__ = [
    # Standard format
    'StandardResult',
    # State definitions
    'SharedState',
    'SearchTeamState',
    'DocumentTeamState',
    'AnalysisTeamState',
    'PlanningState',
    'MainSupervisorState',
    # Supporting types
    'SearchKeywords',
    'DocumentTemplate',
    'DocumentContent',
    'ReviewResult',
    'AnalysisInput',
    'AnalysisMetrics',
    'AnalysisInsight',
    'AnalysisReport',
    # Utilities
    'StateManager',
    'StateValidator',
    'StateTransition'
]