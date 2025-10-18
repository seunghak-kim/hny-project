"""
Execution Orchestrator - 실행 중 동적 조율 전담
기존 인프라를 최대한 활용하는 최소 구현

기존 활용:
- StateManager의 update_step_status 메서드
- ExecutionStepState 구조
- WebSocket progress_callback
- Long-term Memory Service
- PostgreSQL Checkpointing
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 기존 인프라 import
from app.service_agent.foundation.separated_states import (
    MainSupervisorState,
    ExecutionStepState,
    StateManager,
    PlanningState
)
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService
from app.service_agent.llm_manager import LLMService
from app.db.postgre_db import get_async_db


@dataclass
class OrchestrationDecision:
    """오케스트레이션 결정 기록"""
    phase: str
    decision_type: str
    decision: Dict[str, Any]
    reasoning: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ExecutionOrchestrator:
    """
    실행 중 동적 조율을 담당하는 Cognitive Agent
    기존 인프라를 최대한 활용하여 최소 변경으로 구현
    """

    def __init__(self, llm_context=None):
        """초기화"""
        self.llm_context = llm_context
        self.llm_service = LLMService(llm_context=llm_context)
        self.state_manager = StateManager()  # 기존 StateManager 활용
        self.memory_service = None  # 동적 초기화

        # 결정 기록
        self.decisions: List[OrchestrationDecision] = []
        self.llm_call_count = 0

        # 학습된 패턴
        self.learned_patterns: Dict[str, Any] = {}
        self.tool_success_rates: Dict[str, float] = {}

        logger.info("[ExecutionOrchestrator] Initialized with existing infrastructure")

    async def orchestrate_with_state(
        self,
        state: MainSupervisorState,
        progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None
    ) -> MainSupervisorState:
        """
        기존 State 구조를 그대로 받아서 처리

        Args:
            state: MainSupervisorState (기존 구조 그대로)
            progress_callback: WebSocket callback (기존 시스템 활용)

        Returns:
            업데이트된 MainSupervisorState
        """
        logger.info("[ExecutionOrchestrator] Starting orchestration with existing state")

        # 1. 기존 planning_state와 execution_steps 활용
        planning_state = state.get("planning_state", {})
        execution_steps = planning_state.get("execution_steps", [])

        if not execution_steps:
            logger.warning("[ExecutionOrchestrator] No execution steps found, skipping orchestration")
            return state

        # 2. Long-term Memory에서 패턴 로드 (user_id가 있는 경우)
        user_id = state.get("user_id")
        if user_id:
            await self._load_user_patterns(user_id)

        # 3. WebSocket 알림: 오케스트레이션 시작
        if progress_callback:
            try:
                await progress_callback("orchestration_started", {
                    "message": "실행 전략을 최적화하고 있습니다...",
                    "total_steps": len(execution_steps)
                })
            except Exception as e:
                logger.error(f"[ExecutionOrchestrator] Failed to send WebSocket: {e}")

        # 4. 실행 전략 결정 (LLM 호출)
        strategy = await self._decide_execution_strategy(
            query=state.get("query", ""),
            execution_steps=execution_steps,
            previous_results=state.get("team_results", {}),
            learned_patterns=self.learned_patterns
        )

        # 5. 도구 선택 최적화 (전역 관점)
        tool_selections = await self._optimize_tool_selection(
            query=state.get("query", ""),
            execution_steps=execution_steps,
            user_patterns=self.learned_patterns
        )

        # 6. 기존 StateManager를 활용한 상태 업데이트
        for step in execution_steps:
            step_id = step.get("step_id")
            team = step.get("team")

            # 오케스트레이션 메타데이터 추가
            step["orchestration"] = {
                "strategy": strategy.get("strategy", "sequential"),
                "selected_tools": tool_selections.get(team, []),
                "priority": strategy.get("priorities", {}).get(team, 1),
                "estimated_time": strategy.get("estimated_times", {}).get(team, 10)
            }

            # StateManager의 기존 메서드 활용
            planning_state = self.state_manager.update_step_status(
                planning_state,
                step_id,
                "pending",  # 상태는 유지, 메타데이터만 추가
                progress=5  # 오케스트레이션 완료 = 5%
            )

        # 7. WebSocket 알림: 오케스트레이션 완료
        if progress_callback:
            try:
                await progress_callback("orchestration_complete", {
                    "message": "실행 전략 최적화 완료",
                    "strategy": strategy.get("strategy"),
                    "tool_selections": tool_selections,
                    "execution_steps": execution_steps
                })
            except Exception as e:
                logger.error(f"[ExecutionOrchestrator] Failed to send WebSocket: {e}")

        # 8. State 업데이트
        state["planning_state"] = planning_state

        # 오케스트레이션 메타데이터 추가 (체크포인트에 저장됨)
        state["orchestration_metadata"] = {
            "strategy": strategy,
            "tool_selections": tool_selections,
            "decisions": [self._serialize_decision(d) for d in self.decisions],
            "llm_calls": self.llm_call_count,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"[ExecutionOrchestrator] Orchestration complete: {strategy.get('strategy')} strategy, {self.llm_call_count} LLM calls")

        return state

    async def analyze_team_result(
        self,
        state: MainSupervisorState,
        team_name: str,
        team_result: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> MainSupervisorState:
        """
        팀 실행 후 결과 분석 및 다음 단계 결정

        team_supervisor의 after_team 훅에서 호출
        """
        logger.info(f"[ExecutionOrchestrator] Analyzing result from {team_name}")

        # 1. 결과 품질 평가 (LLM)
        quality_analysis = await self._analyze_result_quality(
            team_name=team_name,
            result=team_result,
            query=state.get("query", "")
        )

        # 2. 다음 팀을 위한 조정 결정
        if quality_analysis.get("quality_score", 0) < 0.5:
            logger.warning(f"[ExecutionOrchestrator] Low quality from {team_name}: {quality_analysis.get('quality_score')}")

            # 다음 팀 전략 조정
            adjustments = await self._decide_adjustments(
                low_quality_team=team_name,
                remaining_teams=self._get_remaining_teams(state),
                quality_analysis=quality_analysis
            )

            # State에 조정사항 반영
            state["execution_adjustments"] = adjustments

        # 3. 학습: 결과를 Memory에 저장
        user_id = state.get("user_id")
        if user_id:
            await self._save_execution_result(
                user_id=user_id,
                team_name=team_name,
                tools_used=team_result.get("sources_used", []),
                quality_score=quality_analysis.get("quality_score", 0),
                execution_time=team_result.get("execution_time", 0)
            )

        # 4. WebSocket 알림
        if progress_callback:
            await progress_callback("team_analysis_complete", {
                "team": team_name,
                "quality_score": quality_analysis.get("quality_score"),
                "adjustments": state.get("execution_adjustments")
            })

        return state

    async def _decide_execution_strategy(
        self,
        query: str,
        execution_steps: List[Dict],
        previous_results: Dict,
        learned_patterns: Dict
    ) -> Dict[str, Any]:
        """실행 전략 결정 (LLM 호출)"""

        try:
            # LLM 프롬프트 준비
            result = await self.llm_service.complete_json_async(
                prompt_name="orchestration/execution_strategy",
                variables={
                    "query": query,
                    "execution_steps": execution_steps,
                    "previous_results": self._summarize_results(previous_results),
                    "learned_patterns": learned_patterns
                },
                temperature=0.1,
                max_tokens=600
            )

            # 결정 기록
            self._log_decision(
                phase="strategy",
                decision_type="execution_strategy",
                decision=result,
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.7)
            )

            self.llm_call_count += 1

            return result

        except Exception as e:
            logger.error(f"[ExecutionOrchestrator] Strategy decision failed: {e}")
            # Fallback
            return {
                "strategy": "sequential",
                "reasoning": "Fallback due to LLM error",
                "confidence": 0.3
            }

    async def _optimize_tool_selection(
        self,
        query: str,
        execution_steps: List[Dict],
        user_patterns: Dict
    ) -> Dict[str, List[str]]:
        """전역 관점에서 도구 선택 최적화"""

        try:
            # 각 팀별 도구 선택
            tool_selections = {}

            for step in execution_steps:
                team = step.get("team")

                # Skip if not a team that uses tools
                if team not in ["search", "analysis", "document"]:
                    continue

                # LLM으로 도구 선택
                result = await self.llm_service.complete_json_async(
                    prompt_name="orchestration/tool_selection",
                    variables={
                        "query": query,
                        "team": team,
                        "already_selected": tool_selections,
                        "user_patterns": user_patterns,
                        "tool_success_rates": self.tool_success_rates
                    },
                    temperature=0.1,
                    max_tokens=400
                )

                tool_selections[team] = result.get("selected_tools", [])
                self.llm_call_count += 1

            # 결정 기록
            self._log_decision(
                phase="tool_selection",
                decision_type="global_tool_optimization",
                decision=tool_selections,
                reasoning="Optimized to avoid duplication",
                confidence=0.8
            )

            return tool_selections

        except Exception as e:
            logger.error(f"[ExecutionOrchestrator] Tool selection failed: {e}")
            return {}

    async def _load_user_patterns(self, user_id: int):
        """사용자 실행 패턴 로드"""
        try:
            async with get_async_db() as db:
                memory_service = LongTermMemoryService(db)

                # 최근 실행 패턴 로드
                memories = await memory_service.load_recent_memories(
                    user_id=user_id,
                    limit=10,
                    relevance_filter="EXECUTION_PATTERN"
                )

                # 패턴 분석
                for memory in memories:
                    content = memory.get("content", {})
                    if isinstance(content, str):
                        try:
                            content = json.loads(content)
                        except:
                            continue

                    # 성공한 도구 학습
                    if content.get("success"):
                        for tool in content.get("tools", []):
                            self.tool_success_rates[tool] = self.tool_success_rates.get(tool, 0.5) * 0.9 + 0.1

                self.learned_patterns = {
                    "tool_success_rates": self.tool_success_rates,
                    "pattern_count": len(memories)
                }

                logger.info(f"[ExecutionOrchestrator] Loaded {len(memories)} patterns for user {user_id}")

        except Exception as e:
            logger.error(f"[ExecutionOrchestrator] Failed to load patterns: {e}")

    async def _save_execution_result(
        self,
        user_id: int,
        team_name: str,
        tools_used: List[str],
        quality_score: float,
        execution_time: float
    ):
        """실행 결과를 Memory에 저장"""
        try:
            async with get_async_db() as db:
                memory_service = LongTermMemoryService(db)

                pattern = {
                    "team": team_name,
                    "tools": tools_used,
                    "quality_score": quality_score,
                    "execution_time": execution_time,
                    "success": quality_score > 0.7,
                    "timestamp": datetime.now().isoformat()
                }

                # Memory에 저장 (conversation_memories 테이블 활용)
                await memory_service.save_memory(
                    user_id=user_id,
                    memory_type="EXECUTION_PATTERN",
                    content=json.dumps(pattern),
                    metadata={
                        "team": team_name,
                        "quality_score": quality_score
                    }
                )

                logger.info(f"[ExecutionOrchestrator] Saved execution pattern for team {team_name}")

        except Exception as e:
            logger.error(f"[ExecutionOrchestrator] Failed to save pattern: {e}")

    async def _analyze_result_quality(
        self,
        team_name: str,
        result: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """결과 품질 분석"""
        try:
            # 간단한 휴리스틱 (LLM 호출 최소화)
            quality_score = 0.7  # 기본값

            if team_name == "search":
                # 검색 결과 수로 품질 판단
                total_results = result.get("total_results", 0)
                if total_results > 10:
                    quality_score = 0.9
                elif total_results > 5:
                    quality_score = 0.7
                else:
                    quality_score = 0.5

            elif team_name == "analysis":
                # 분석 신뢰도로 품질 판단
                confidence = result.get("confidence_score", 0)
                quality_score = confidence

            return {
                "quality_score": quality_score,
                "assessment": "Heuristic evaluation",
                "factors": {
                    "result_count": result.get("total_results", 0),
                    "confidence": result.get("confidence_score", 0)
                }
            }

        except Exception as e:
            logger.error(f"[ExecutionOrchestrator] Quality analysis failed: {e}")
            return {"quality_score": 0.5, "assessment": "Error in analysis"}

    async def _decide_adjustments(
        self,
        low_quality_team: str,
        remaining_teams: List[str],
        quality_analysis: Dict
    ) -> Dict[str, Any]:
        """품질이 낮을 때 조정 결정"""
        adjustments = {
            "reason": f"Low quality from {low_quality_team}",
            "quality_score": quality_analysis.get("quality_score"),
            "actions": []
        }

        # 간단한 규칙 기반 조정
        if low_quality_team == "search" and "analysis" in remaining_teams:
            adjustments["actions"].append({
                "team": "analysis",
                "adjustment": "reduce_scope",
                "reason": "Limited search results"
            })

        return adjustments

    def _log_decision(
        self,
        phase: str,
        decision_type: str,
        decision: Dict[str, Any],
        reasoning: str,
        confidence: float
    ):
        """결정 기록"""
        self.decisions.append(
            OrchestrationDecision(
                phase=phase,
                decision_type=decision_type,
                decision=decision,
                reasoning=reasoning,
                confidence=confidence
            )
        )
        logger.info(f"[ExecutionOrchestrator] Decision logged: {phase}/{decision_type}, confidence: {confidence}")

    def _serialize_decision(self, decision: OrchestrationDecision) -> Dict:
        """결정을 직렬화"""
        return {
            "phase": decision.phase,
            "type": decision.decision_type,
            "decision": decision.decision,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp
        }

    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """결과 요약"""
        summary = {}
        for team, result in results.items():
            if isinstance(result, dict):
                summary[team] = {
                    "status": result.get("status", "unknown"),
                    "result_count": result.get("total_results", 0),
                    "execution_time": result.get("execution_time", 0)
                }
        return summary

    def _get_remaining_teams(self, state: MainSupervisorState) -> List[str]:
        """남은 팀 목록"""
        active_teams = state.get("active_teams", [])
        completed_teams = state.get("completed_teams", [])
        return [t for t in active_teams if t not in completed_teams]

    def get_summary(self) -> str:
        """오케스트레이션 요약"""
        return (
            f"Orchestration Summary: "
            f"{self.llm_call_count} LLM calls, "
            f"{len(self.decisions)} decisions, "
            f"{len(self.learned_patterns)} patterns learned"
        )