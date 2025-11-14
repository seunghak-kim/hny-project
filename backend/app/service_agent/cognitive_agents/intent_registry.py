"""
Intent Registry - Description 기반 Intent 관리
YAML 설정 파일에서 Intent 정의를 로드하고 중앙 관리
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class IntentDefinition:
    """
    Intent 정의 (Description 기반)

    Attributes:
        name: Intent 이름 (UPPERCASE)
        display_name: 사용자에게 보여질 이름 (한글)
        description: Intent에 대한 상세 설명
        category: Intent 카테고리 (검색, 분석, 문서생성 등)
        tools: 사용되는 도구 목록
        agents: 처리할 에이전트 목록
        question_patterns: 질문 패턴 목록
        examples: 실제 사용자 질문 예시
        complexity: 복잡도 (low, medium, high)
        requires_analysis: 분석이 필요한지 여부
        analysis_keywords: 분석 필요 여부를 판단할 키워드
        enabled: 활성화 여부
        priority: 우선순위 (낮을수록 높은 우선순위)
        metadata: 추가 메타데이터
    """
    name: str
    display_name: str
    description: str
    category: str
    tools: List[str]
    agents: List[str]
    question_patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    complexity: str = "medium"  # low, medium, high
    requires_analysis: bool = False
    analysis_keywords: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Dictionary로 변환"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "tools": self.tools,
            "agents": self.agents,
            "question_patterns": self.question_patterns,
            "examples": self.examples,
            "complexity": self.complexity,
            "requires_analysis": self.requires_analysis,
            "analysis_keywords": self.analysis_keywords,
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": self.metadata
        }


class IntentRegistry:
    """
    Intent 정의를 중앙 관리하는 Registry

    YAML 설정 파일에서 Intent 정의를 로드하고,
    Description 기반으로 동적으로 프롬프트를 생성
    """

    _intents: Dict[str, IntentDefinition] = {}
    _initialized = False
    _config_path: Optional[Path] = None

    @classmethod
    def initialize(cls, config_path: Optional[str] = None):
        """
        YAML 설정에서 Intent 정의 로드

        Args:
            config_path: YAML 설정 파일 경로 (None이면 기본 경로 사용)
        """
        if cls._initialized:
            logger.debug("IntentRegistry already initialized")
            return

        if config_path is None:
            # 기본 경로: backend/app/service_agent/config/intent_definitions.yaml
            config_path = Path(__file__).parent.parent / "config" / "intent_definitions.yaml"
        else:
            config_path = Path(config_path)

        cls._config_path = config_path

        if not config_path.exists():
            logger.error(f"Intent definitions file not found: {config_path}")
            raise FileNotFoundError(f"Intent definitions file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config or 'intents' not in config:
                logger.error("Invalid intent definitions file: missing 'intents' key")
                raise ValueError("Invalid intent definitions file")

            # Intent 정의 로드
            for intent_data in config['intents']:
                intent_def = IntentDefinition(
                    name=intent_data['name'],
                    display_name=intent_data['display_name'],
                    description=intent_data['description'],
                    category=intent_data.get('category', '기타'),
                    tools=intent_data.get('tools', []),
                    agents=intent_data.get('agents', []),
                    question_patterns=intent_data.get('question_patterns', []),
                    examples=intent_data.get('examples', []),
                    complexity=intent_data.get('complexity', 'medium'),
                    requires_analysis=intent_data.get('requires_analysis', False),
                    analysis_keywords=intent_data.get('analysis_keywords', []),
                    enabled=intent_data.get('enabled', True),
                    priority=intent_data.get('priority', 50),
                    metadata=intent_data.get('metadata', {})
                )
                cls._intents[intent_def.name] = intent_def

            cls._initialized = True
            logger.info(f"IntentRegistry initialized with {len(cls._intents)} intents from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load intent definitions: {e}")
            raise

    @classmethod
    def reload(cls):
        """설정 파일 다시 로드 (런타임 업데이트)"""
        cls._initialized = False
        cls._intents.clear()
        cls.initialize(str(cls._config_path) if cls._config_path else None)
        logger.info("IntentRegistry reloaded")

    @classmethod
    def get_intent(cls, name: str) -> Optional[IntentDefinition]:
        """
        Intent 정의 조회

        Args:
            name: Intent 이름

        Returns:
            IntentDefinition 또는 None
        """
        if not cls._initialized:
            cls.initialize()
        return cls._intents.get(name)

    @classmethod
    def list_intents(cls, enabled_only: bool = False) -> List[str]:
        """
        모든 Intent 이름 목록

        Args:
            enabled_only: True면 활성화된 Intent만 반환

        Returns:
            Intent 이름 목록
        """
        if not cls._initialized:
            cls.initialize()

        if enabled_only:
            return [name for name, intent in cls._intents.items() if intent.enabled]
        return list(cls._intents.keys())

    @classmethod
    def get_all_intents(cls, enabled_only: bool = False) -> Dict[str, IntentDefinition]:
        """
        모든 Intent 정의

        Args:
            enabled_only: True면 활성화된 Intent만 반환

        Returns:
            Intent 정의 딕셔너리
        """
        if not cls._initialized:
            cls.initialize()

        if enabled_only:
            return {name: intent for name, intent in cls._intents.items() if intent.enabled}
        return cls._intents.copy()

    @classmethod
    def get_intents_by_category(cls, category: str) -> List[IntentDefinition]:
        """
        카테고리별 Intent 조회

        Args:
            category: 카테고리 이름

        Returns:
            해당 카테고리의 Intent 목록
        """
        if not cls._initialized:
            cls.initialize()

        return [
            intent for intent in cls._intents.values()
            if intent.category == category and intent.enabled
        ]

    @classmethod
    def generate_prompt_section(cls, intent_name: str, include_examples: int = 3) -> str:
        """
        특정 Intent에 대한 프롬프트 섹션 동적 생성

        Args:
            intent_name: Intent 이름
            include_examples: 포함할 예시 개수

        Returns:
            프롬프트 섹션 문자열
        """
        intent = cls.get_intent(intent_name)
        if not intent:
            return ""

        # 예시 제한
        examples = intent.examples[:include_examples] if include_examples > 0 else intent.examples

        prompt = f"""### {intent.display_name} ({intent.name})
**설명**: {intent.description.strip()}
**카테고리**: {intent.category}
**복잡도**: {intent.complexity}

**질문 패턴**:
{chr(10).join(f'  - {pattern}' for pattern in intent.question_patterns) if intent.question_patterns else '  (없음)'}

**예시**:
{chr(10).join(f'  - {example}' for example in examples) if examples else '  (없음)'}
"""
        return prompt

    @classmethod
    def generate_full_prompt(cls, enabled_only: bool = True, include_examples: int = 3) -> str:
        """
        전체 Intent 카테고리에 대한 프롬프트 동적 생성

        Args:
            enabled_only: True면 활성화된 Intent만 포함
            include_examples: 각 Intent당 포함할 예시 개수

        Returns:
            전체 프롬프트 문자열
        """
        if not cls._initialized:
            cls.initialize()

        intents = cls.get_all_intents(enabled_only=enabled_only)

        # 우선순위 순으로 정렬
        sorted_intents = sorted(intents.values(), key=lambda x: x.priority)

        sections = []
        for intent in sorted_intents:
            sections.append(cls.generate_prompt_section(intent.name, include_examples))

        return "\n".join(sections)

    @classmethod
    def generate_compact_definitions(cls, enabled_only: bool = True) -> str:
        """
        LLM에 전달할 간단한 Intent 정의 생성 (JSON 형식)

        Args:
            enabled_only: True면 활성화된 Intent만 포함

        Returns:
            JSON 문자열
        """
        if not cls._initialized:
            cls.initialize()

        intents = cls.get_all_intents(enabled_only=enabled_only)
        sorted_intents = sorted(intents.values(), key=lambda x: x.priority)

        definitions = []
        for intent in sorted_intents:
            definitions.append({
                "name": intent.name,
                "display_name": intent.display_name,
                "description": intent.description.strip(),
                "category": intent.category,
                "examples": intent.examples[:2],  # 예시 2개만
                "complexity": intent.complexity
            })

        return json.dumps(definitions, ensure_ascii=False, indent=2)

    @classmethod
    def add_intent(cls, intent_def: IntentDefinition):
        """
        런타임에 새로운 Intent 추가 (확장성)

        Args:
            intent_def: Intent 정의
        """
        if not cls._initialized:
            cls.initialize()

        cls._intents[intent_def.name] = intent_def
        logger.info(f"Intent '{intent_def.name}' added to registry")

    @classmethod
    def update_intent(cls, intent_name: str, updates: Dict[str, Any]):
        """
        Intent 정의 업데이트

        Args:
            intent_name: Intent 이름
            updates: 업데이트할 필드
        """
        if not cls._initialized:
            cls.initialize()

        intent = cls._intents.get(intent_name)
        if not intent:
            logger.warning(f"Intent '{intent_name}' not found")
            return

        # dataclass 필드 업데이트
        for key, value in updates.items():
            if hasattr(intent, key):
                setattr(intent, key, value)

        logger.info(f"Intent '{intent_name}' updated: {updates}")

    @classmethod
    def disable_intent(cls, intent_name: str):
        """Intent 비활성화"""
        cls.update_intent(intent_name, {"enabled": False})

    @classmethod
    def enable_intent(cls, intent_name: str):
        """Intent 활성화"""
        cls.update_intent(intent_name, {"enabled": True})

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Registry 통계 정보

        Returns:
            통계 정보 딕셔너리
        """
        if not cls._initialized:
            cls.initialize()

        total = len(cls._intents)
        enabled = sum(1 for intent in cls._intents.values() if intent.enabled)
        by_category = {}

        for intent in cls._intents.values():
            category = intent.category
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1

        return {
            "total_intents": total,
            "enabled_intents": enabled,
            "disabled_intents": total - enabled,
            "by_category": by_category,
            "config_path": str(cls._config_path)
        }


# 사용 예시
if __name__ == "__main__":
    # Registry 초기화
    IntentRegistry.initialize()

    # 통계 출력
    stats = IntentRegistry.get_statistics()
    print(f"Intent Registry Statistics:")
    print(f"  Total: {stats['total_intents']}")
    print(f"  Enabled: {stats['enabled_intents']}")
    print(f"  By Category: {stats['by_category']}")

    # Intent 조회
    legal_intent = IntentRegistry.get_intent("LEGAL_INQUIRY")
    if legal_intent:
        print(f"\nLegal Inquiry Intent:")
        print(f"  Display Name: {legal_intent.display_name}")
        print(f"  Description: {legal_intent.description[:100]}...")
        print(f"  Agents: {legal_intent.agents}")

    # 프롬프트 생성
    print("\n--- Generated Prompt Section ---")
    print(IntentRegistry.generate_prompt_section("TERM_DEFINITION"))

    # 간단한 정의 생성
    print("\n--- Compact Definitions (JSON) ---")
    print(IntentRegistry.generate_compact_definitions()[:500] + "...")
