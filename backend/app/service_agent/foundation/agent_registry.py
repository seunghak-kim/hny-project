"""
Agent Registry System
중앙화된 Agent 관리 시스템 - 동적 Agent 로딩 및 실행 지원
"""

from typing import Type, Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class AgentCapabilities:
    """Agent 능력 정의"""

    def __init__(
        self,
        name: str,
        description: str,
        input_types: List[str],
        output_types: List[str],
        required_tools: List[str] = None,
        team: str = None
    ):
        self.name = name
        self.description = description
        self.input_types = input_types
        self.output_types = output_types
        self.required_tools = required_tools or []
        self.team = team


class AgentMetadata:
    """Agent 메타데이터"""

    def __init__(
        self,
        agent_class: Type,
        team: Optional[str] = None,
        capabilities: Optional[AgentCapabilities] = None,
        priority: int = 0,
        enabled: bool = True
    ):
        self.agent_class = agent_class
        self.team = team
        self.capabilities = capabilities
        self.priority = priority
        self.enabled = enabled


class AgentRegistry:
    """
    중앙 Agent 레지스트리
    모든 Agent를 동적으로 등록하고 관리
    """

    _instance = None
    _agents: Dict[str, AgentMetadata] = {}
    _teams: Dict[str, List[str]] = {}
    _initialization_hooks: List[Callable] = []

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(
        cls,
        name: str,
        agent_class: Type,
        team: Optional[str] = None,
        capabilities: Optional[AgentCapabilities] = None,
        priority: int = 0,
        enabled: bool = True
    ) -> None:
        """
        Agent를 레지스트리에 등록

        Args:
            name: Agent 이름 (unique identifier)
            agent_class: Agent 클래스
            team: 소속 팀 (optional)
            capabilities: Agent 능력 정의
            priority: 실행 우선순위 (높을수록 먼저 실행)
            enabled: 활성화 여부
        """
        if name in cls._agents:
            logger.warning(f"Agent '{name}' is already registered. Overwriting...")

        metadata = AgentMetadata(
            agent_class=agent_class,
            team=team,
            capabilities=capabilities,
            priority=priority,
            enabled=enabled
        )

        cls._agents[name] = metadata

        # 팀별 분류
        if team:
            if team not in cls._teams:
                cls._teams[team] = []
            if name not in cls._teams[team]:
                cls._teams[team].append(name)

        logger.info(f"Agent '{name}' registered successfully (team: {team}, enabled: {enabled})")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Agent 등록 해제"""
        if name not in cls._agents:
            logger.warning(f"Agent '{name}' not found in registry")
            return False

        metadata = cls._agents[name]

        # 팀에서 제거
        if metadata.team and metadata.team in cls._teams:
            cls._teams[metadata.team].remove(name)
            if not cls._teams[metadata.team]:
                del cls._teams[metadata.team]

        del cls._agents[name]
        logger.info(f"Agent '{name}' unregistered successfully")
        return True

    @classmethod
    def get_agent(cls, name: str) -> Optional[AgentMetadata]:
        """특정 Agent 메타데이터 조회"""
        return cls._agents.get(name)

    @classmethod
    def get_agent_class(cls, name: str) -> Optional[Type]:
        """Agent 클래스 조회"""
        metadata = cls._agents.get(name)
        return metadata.agent_class if metadata else None

    @classmethod
    def create_agent(cls, name: str, **kwargs) -> Optional[Any]:
        """
        Agent 인스턴스 생성

        Args:
            name: Agent 이름
            **kwargs: Agent 생성자 인자

        Returns:
            Agent 인스턴스 또는 None
        """
        metadata = cls._agents.get(name)
        if not metadata:
            logger.error(f"Agent '{name}' not found in registry")
            return None

        if not metadata.enabled:
            logger.warning(f"Agent '{name}' is disabled")
            return None

        try:
            agent_instance = metadata.agent_class(**kwargs)
            logger.debug(f"Agent '{name}' instance created successfully")
            return agent_instance
        except Exception as e:
            logger.error(f"Failed to create agent '{name}': {e}")
            return None

    @classmethod
    def list_agents(cls, team: Optional[str] = None, enabled_only: bool = True) -> List[str]:
        """
        Agent 목록 조회

        Args:
            team: 특정 팀의 Agent만 조회
            enabled_only: 활성화된 Agent만 조회

        Returns:
            Agent 이름 목록
        """
        if team:
            agent_names = cls._teams.get(team, [])
        else:
            agent_names = list(cls._agents.keys())

        if enabled_only:
            agent_names = [
                name for name in agent_names
                if cls._agents[name].enabled
            ]

        # 우선순위 순으로 정렬
        agent_names.sort(
            key=lambda name: cls._agents[name].priority,
            reverse=True
        )

        return agent_names

    @classmethod
    def list_teams(cls) -> List[str]:
        """팀 목록 조회"""
        return list(cls._teams.keys())

    @classmethod
    def get_team_agents(cls, team: str, enabled_only: bool = True) -> List[str]:
        """특정 팀의 Agent 목록 조회"""
        return cls.list_agents(team=team, enabled_only=enabled_only)

    @classmethod
    def get_capabilities(cls, name: str) -> Optional[AgentCapabilities]:
        """Agent 능력 조회"""
        metadata = cls._agents.get(name)
        return metadata.capabilities if metadata else None

    @classmethod
    def find_agents_by_capability(
        cls,
        input_type: Optional[str] = None,
        output_type: Optional[str] = None,
        required_tool: Optional[str] = None
    ) -> List[str]:
        """
        능력 기준으로 Agent 검색

        Args:
            input_type: 입력 타입
            output_type: 출력 타입
            required_tool: 필요한 도구

        Returns:
            조건에 맞는 Agent 이름 목록
        """
        matching_agents = []

        for name, metadata in cls._agents.items():
            if not metadata.enabled or not metadata.capabilities:
                continue

            capabilities = metadata.capabilities

            # 조건 검사
            if input_type and input_type not in capabilities.input_types:
                continue
            if output_type and output_type not in capabilities.output_types:
                continue
            if required_tool and required_tool not in capabilities.required_tools:
                continue

            matching_agents.append(name)

        return matching_agents

    @classmethod
    def set_enabled(cls, name: str, enabled: bool) -> bool:
        """Agent 활성화/비활성화"""
        metadata = cls._agents.get(name)
        if not metadata:
            logger.error(f"Agent '{name}' not found")
            return False

        metadata.enabled = enabled
        logger.info(f"Agent '{name}' {'enabled' if enabled else 'disabled'}")
        return True

    @classmethod
    def add_initialization_hook(cls, hook: Callable) -> None:
        """Agent 초기화 훅 추가"""
        cls._initialization_hooks.append(hook)

    @classmethod
    def initialize_all(cls, **kwargs) -> Dict[str, Any]:
        """
        모든 등록된 Agent 초기화

        Returns:
            초기화된 Agent 인스턴스 딕셔너리
        """
        initialized_agents = {}

        for name in cls.list_agents(enabled_only=True):
            agent = cls.create_agent(name, **kwargs)
            if agent:
                initialized_agents[name] = agent

        # 초기화 훅 실행
        for hook in cls._initialization_hooks:
            hook(initialized_agents)

        logger.info(f"Initialized {len(initialized_agents)} agents")
        return initialized_agents

    @classmethod
    def clear(cls) -> None:
        """레지스트리 초기화 (테스트용)"""
        cls._agents.clear()
        cls._teams.clear()
        cls._initialization_hooks.clear()
        logger.info("Agent registry cleared")


# 데코레이터를 통한 자동 등록
def register_agent(
    name: str,
    team: Optional[str] = None,
    capabilities: Optional[AgentCapabilities] = None,
    priority: int = 0,
    enabled: bool = True
):
    """
    Agent 클래스 데코레이터

    Usage:
        @register_agent("search_agent", team="search", priority=10)
        class SearchAgent:
            pass
    """
    def decorator(agent_class: Type) -> Type:
        AgentRegistry.register(
            name=name,
            agent_class=agent_class,
            team=team,
            capabilities=capabilities,
            priority=priority,
            enabled=enabled
        )
        return agent_class

    return decorator


# 사용 예시를 위한 타입 정의
if __name__ == "__main__":
    # 테스트용 Agent 클래스
    class TestAgent:
        def __init__(self, config=None):
            self.config = config

        def execute(self, input_data):
            return {"status": "completed", "data": input_data}

    # Agent 등록
    capabilities = AgentCapabilities(
        name="test_agent",
        description="테스트용 Agent",
        input_types=["text", "query"],
        output_types=["result"],
        required_tools=["test_tool"]
    )

    AgentRegistry.register(
        name="test_agent",
        agent_class=TestAgent,
        team="test_team",
        capabilities=capabilities,
        priority=5
    )

    # Agent 조회 및 생성
    print(f"Registered agents: {AgentRegistry.list_agents()}")
    print(f"Teams: {AgentRegistry.list_teams()}")

    agent = AgentRegistry.create_agent("test_agent", config={"test": True})
    if agent:
        result = agent.execute({"query": "test"})
        print(f"Execution result: {result}")