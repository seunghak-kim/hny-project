"""
Agent Adapter - 기존 Agent들을 Registry 시스템에 통합
기존 코드를 최소한으로 수정하면서 새로운 아키텍처 적용
"""

import logging
from typing import Dict, Any, Optional, Type
from app.service_agent.foundation.agent_registry import AgentRegistry, AgentCapabilities

logger = logging.getLogger(__name__)


class AgentAdapter:
    """
    기존 Agent들을 Registry와 통합하는 어댑터
    """

    @staticmethod
    def register_existing_agents():
        """
        Team-based 아키텍처를 위한 팀/에이전트 등록
        """
        logger.info("Registering teams to Registry...")

        # SearchTeam 등록 (가상 에이전트로 등록)
        try:
            # 팀을 가상 에이전트로 등록하여 PlanningAgent가 인식할 수 있도록 함
            capabilities = AgentCapabilities(
                name="search_team",
                description="법률, 부동산, 대출 정보를 검색하는 팀",
                input_types=["query", "keywords"],
                output_types=["legal_search", "real_estate_search", "loan_search"],
                required_tools=[
                    "legal_search_tool",
                    "real_estate_search_tool",
                    "loan_search_tool"
                ],
                team="search"
            )

            # 팀을 더미 클래스로 등록 (실제 팀 수퍼바이저는 별도로 인스턴스화됨)
            class SearchTeamPlaceholder:
                pass

            AgentRegistry.register(
                name="search_team",
                agent_class=SearchTeamPlaceholder,
                team="search",
                capabilities=capabilities,
                priority=10,
                enabled=True
            )
            logger.info("SearchTeam registered successfully")

        except Exception as e:
            logger.error(f"Failed to register SearchTeam: {e}")

        # AnalysisTeam 등록
        try:
            capabilities = AgentCapabilities(
                name="analysis_team",
                description="수집된 데이터를 분석하고 보고서를 생성하는 팀",
                input_types=["collected_data", "analysis_type", "property_data", "user_profile"],
                output_types=["report", "insights", "recommendations", "roi_metrics", "risk_assessment"],
                required_tools=[
                    "contract_analysis_tool",
                    "market_analysis_tool",
                    "roi_calculator_tool",
                    "loan_simulator_tool",
                    "policy_matcher_tool"
                ],
                team="analysis"
            )

            class AnalysisTeamPlaceholder:
                pass

            AgentRegistry.register(
                name="analysis_team",
                agent_class=AnalysisTeamPlaceholder,
                team="analysis",
                capabilities=capabilities,
                priority=5,
                enabled=True
            )
            logger.info("AnalysisTeam registered successfully")

        except Exception as e:
            logger.error(f"Failed to register AnalysisTeam: {e}")

        # DocumentTeam 등록
        try:
            capabilities = AgentCapabilities(
                name="document_team",
                description="부동산 관련 법률 문서를 생성하는 팀",
                input_types=["document_type", "document_params"],
                output_types=["generated_document"],
                required_tools=["document_generation_tool"],
                team="document"
            )

            class DocumentTeamPlaceholder:
                pass

            AgentRegistry.register(
                name="document_team",
                agent_class=DocumentTeamPlaceholder,
                team="document",
                capabilities=capabilities,
                priority=3,
                enabled=True
            )
            logger.info("DocumentTeam registered successfully")

        except Exception as e:
            logger.error(f"Failed to register DocumentTeam: {e}")

        # 나중에 추가할 팀들을 위한 플레이스홀더

        logger.info(f"Registration complete. Registered agents: {AgentRegistry.list_agents()}")
        logger.info(f"Teams: {AgentRegistry.list_teams()}")

    @staticmethod
    async def execute_agent_dynamic(
        agent_name: str,
        input_data: Dict[str, Any],
        llm_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Registry를 통해 Agent를 동적으로 실행

        Args:
            agent_name: 실행할 Agent 이름
            input_data: 입력 데이터
            llm_context: LLM 컨텍스트

        Returns:
            실행 결과
        """
        # Registry에서 Agent 클래스 조회
        agent_class = AgentRegistry.get_agent_class(agent_name)
        if not agent_class:
            logger.error(f"Agent '{agent_name}' not found in registry")
            return {
                "status": "error",
                "error": f"Agent '{agent_name}' not found",
                "agent": agent_name
            }

        # Agent 메타데이터 조회
        metadata = AgentRegistry.get_agent(agent_name)
        if not metadata.enabled:
            logger.warning(f"Agent '{agent_name}' is disabled")
            return {
                "status": "skipped",
                "error": f"Agent '{agent_name}' is disabled",
                "agent": agent_name
            }

        try:
            # Agent 인스턴스 생성
            if agent_name in ["search_agent", "analysis_agent"]:
                # LLM context가 필요한 Agent들
                agent = agent_class(llm_context=llm_context)
            else:
                # LLM context가 필요 없는 Agent들
                agent = agent_class()

            # Agent 실행
            if hasattr(agent, 'app') and agent.app:
                # LangGraph 기반 Agent (SearchAgent, AnalysisAgent)
                result = await agent.app.ainvoke(input_data)
            elif hasattr(agent, 'execute'):
                # 일반 Agent (DocumentAgent, ReviewAgent)
                result = await agent.execute(input_data)
            else:
                # 동기 실행 Agent
                result = agent.run(input_data)

            logger.info(f"Agent '{agent_name}' executed successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to execute agent '{agent_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent": agent_name
            }

    @staticmethod
    def get_agent_dependencies(agent_name: str) -> Dict[str, Any]:
        """
        Agent의 의존성 정보 조회
        4개 Agent 간의 의존성 관계 정의

        Args:
            agent_name: Agent 이름

        Returns:
            의존성 정보
        """
        dependencies = {
            "search_agent": {
                "requires": [],
                "provides": ["legal_search", "real_estate_search", "loan_search"],
                "team": "search",
                "description": "정보 검색 Agent - 법률, 부동산, 대출 정보를 검색"
            },
            "analysis_agent": {
                "requires": ["collected_data"],
                "provides": ["report", "insights", "recommendations"],
                "team": "analysis",
                "description": "데이터 분석 Agent - 수집된 데이터를 분석하여 인사이트 도출"
            },
            "document_agent": {
                "requires": ["document_type", "document_params"],
                "provides": ["generated_document"],
                "team": "document",
                "description": "문서 생성 Agent - 계약서 등 법적 문서를 생성"
            },
            "review_agent": {
                "requires": ["document_content"],
                "provides": ["risk_analysis", "recommendations", "compliance_check"],
                "team": "document",
                "description": "문서 검토 Agent - 생성된 문서를 검토하고 위험 요소 분석"
            }
        }

        return dependencies.get(agent_name, {})


# 초기화 함수
def initialize_agent_system(auto_register: bool = True):
    """
    Agent 시스템 초기화

    Args:
        auto_register: 기존 Agent들을 자동으로 등록할지 여부
    """
    if auto_register:
        AgentAdapter.register_existing_agents()

    logger.info("Agent system initialized")
    return AgentRegistry()


# 사용 예시
if __name__ == "__main__":
    import asyncio

    async def test_dynamic_execution():
        # Agent 시스템 초기화
        initialize_agent_system()

        # 동적 Agent 실행 테스트
        test_input = {
            "query": "전세금 인상률 제한은?",
            "chat_session_id": "test_session",
            "original_query": "전세금 인상률 제한은?"
        }

        # Search Agent 실행
        result = await AgentAdapter.execute_agent_dynamic(
            "search_agent",
            test_input
        )
        print(f"Search result: {result.get('status')}")

        # Agent 의존성 정보 조회
        dependencies = AgentAdapter.get_agent_dependencies("search_agent")
        print(f"Search agent dependencies: {dependencies}")

    # 테스트 실행
    asyncio.run(test_dynamic_execution())