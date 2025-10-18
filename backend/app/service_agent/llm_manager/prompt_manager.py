"""
프롬프트 템플릿 관리자 - 코드 블록 안전 처리 버전
- TXT/YAML 파일 로드
- 변수 치환 (코드 블록 보호)
- 프롬프트 캐싱
"""

import logging
import re
import uuid
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class PromptManager:
    """
    프롬프트 템플릿 관리자
    - TXT/YAML 파일 로드
    - 변수 치환 (코드 블록을 안전하게 보호)
    - 프롬프트 캐싱
    """

    def __init__(self, prompts_dir: Path = None):
        """
        초기화

        Args:
            prompts_dir: 프롬프트 디렉토리 (None이면 기본 경로)
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"

        self.prompts_dir = prompts_dir
        self._cache: Dict[str, str] = {}  # 프롬프트 캐시
        self._metadata_cache: Dict[str, Dict] = {}  # 메타데이터 캐시

        logger.debug(f"PromptManager initialized with directory: {self.prompts_dir}")

    def get(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        category: str = None
    ) -> str:
        """
        프롬프트 로드 및 변수 치환

        Args:
            prompt_name: 프롬프트 이름 (예: "intent_analysis")
            variables: 치환할 변수 (예: {"query": "전세 계약은?"})
            category: 카테고리 (cognitive/execution/common, None이면 자동 탐색)

        Returns:
            완성된 프롬프트 문자열
        """
        variables = variables or {}

        # 프롬프트 템플릿 로드 (캐싱 활용)
        template = self._load_template(prompt_name, category)

        # 안전한 변수 치환 (코드 블록 보호)
        try:
            prompt = self._safe_format(template, variables)
            return prompt
        except KeyError as e:
            logger.error(f"Missing variable in prompt {prompt_name}: {e}")
            raise ValueError(f"Missing required variable {e} for prompt '{prompt_name}'")

    def get_with_metadata(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        category: str = None
    ) -> Dict[str, Any]:
        """
        프롬프트와 메타데이터를 함께 반환

        Args:
            prompt_name: 프롬프트 이름
            variables: 치환할 변수
            category: 카테고리

        Returns:
            {"prompt": "...", "metadata": {...}}
        """
        # 프롬프트 로드
        prompt = self.get(prompt_name, variables, category)

        # 메타데이터 로드 (YAML 파일인 경우)
        metadata = self._metadata_cache.get(prompt_name, {})

        return {
            "prompt": prompt,
            "metadata": metadata
        }

    def _safe_format(self, template: str, variables: Dict[str, Any]) -> str:
        """
        코드 블록을 보호하면서 안전하게 변수 치환

        Args:
            template: 프롬프트 템플릿
            variables: 치환할 변수

        Returns:
            변수가 치환된 프롬프트

        Process:
            1. 코드 블록 추출 및 placeholder로 치환
            2. 일반 변수 치환 수행
            3. 코드 블록 복원
        """
        # Step 1: 코드 블록을 임시 placeholder로 치환
        code_blocks = {}

        def save_code_block(match):
            """코드 블록을 저장하고 placeholder 반환"""
            # 고유 ID 생성
            block_id = f"__CODE_BLOCK_{uuid.uuid4().hex}__"

            # 코드 블록 내용 저장
            code_content = match.group(1)

            # escape 처리 제거 ({{ -> {, }} -> })
            # 이미 escape되어 있는 경우 처리
            code_content = code_content.replace('{{', '{').replace('}}', '}')

            # 전체 코드 블록 저장 (```json 포함)
            code_blocks[block_id] = f"```json\n{code_content}\n```"

            # placeholder 반환
            return block_id

        # 모든 코드 블록을 placeholder로 치환
        protected_template = re.sub(
            r'```json\n(.*?)\n```',
            save_code_block,
            template,
            flags=re.DOTALL
        )

        # Step 2: 일반 변수 치환 (코드 블록은 이미 보호됨)
        # 하지만 format()은 여전히 중괄호 안의 줄바꿈을 변수로 인식할 수 있음
        # 따라서 안전한 대체 방법 사용
        formatted = protected_template
        for key, value in variables.items():
            # {variable} 패턴만 정확히 치환
            pattern = '{' + key + '}'
            formatted = formatted.replace(pattern, str(value))

        # Step 3: 코드 블록 복원
        for block_id, code_block in code_blocks.items():
            formatted = formatted.replace(block_id, code_block)

        return formatted

    def _load_template(self, prompt_name: str, category: str = None) -> str:
        """
        프롬프트 템플릿 로드

        Args:
            prompt_name: 프롬프트 이름
            category: 카테고리 (cognitive/execution/common)

        Returns:
            프롬프트 템플릿 문자열

        Raises:
            FileNotFoundError: 프롬프트 파일이 없는 경우
        """
        # 캐시 확인
        cache_key = f"{category}/{prompt_name}" if category else prompt_name
        if cache_key in self._cache:
            logger.debug(f"Using cached prompt: {cache_key}")
            return self._cache[cache_key]

        # 파일 경로 결정
        file_path = self._find_prompt_file(prompt_name, category)

        if not file_path or not file_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {prompt_name} "
                f"(category: {category or 'auto'})"
            )

        # 파일 로드
        logger.debug(f"Loading prompt from: {file_path}")

        if file_path.suffix == ".yaml" or file_path.suffix == ".yml":
            template, metadata = self._load_yaml_template(file_path)
            self._metadata_cache[prompt_name] = metadata
        else:  # .txt
            with open(file_path, 'r', encoding='utf-8') as f:
                template = f.read()

        # 캐시 저장
        self._cache[cache_key] = template

        return template

    def _find_prompt_file(self, prompt_name: str, category: str = None) -> Optional[Path]:
        """
        프롬프트 파일 경로 찾기

        Args:
            prompt_name: 프롬프트 이름
            category: 카테고리

        Returns:
            찾은 파일 경로 또는 None
        """
        # 가능한 확장자
        extensions = ['.txt', '.yaml', '.yml']

        if category:
            # 특정 카테고리 지정
            for ext in extensions:
                file_path = self.prompts_dir / category / f"{prompt_name}{ext}"
                if file_path.exists():
                    return file_path
        else:
            # 모든 카테고리 탐색
            for cat in ["cognitive", "execution", "common"]:
                for ext in extensions:
                    file_path = self.prompts_dir / cat / f"{prompt_name}{ext}"
                    if file_path.exists():
                        return file_path

            # 루트 디렉토리도 확인
            for ext in extensions:
                file_path = self.prompts_dir / f"{prompt_name}{ext}"
                if file_path.exists():
                    return file_path

        return None

    def _load_yaml_template(self, file_path: Path) -> Tuple[str, Dict]:
        """
        YAML 프롬프트 파일 로드

        Args:
            file_path: YAML 파일 경로

        Returns:
            (템플릿 문자열, 메타데이터)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 템플릿 추출
        template = data.get('template', '')

        # 메타데이터 추출
        metadata = {k: v for k, v in data.items() if k != 'template'}

        return template, metadata

    def list_available_prompts(self, category: str = None) -> Dict[str, list]:
        """
        사용 가능한 프롬프트 목록 반환

        Args:
            category: 특정 카테고리만 조회 (None이면 전체)

        Returns:
            {"category": ["prompt1", "prompt2", ...]}
        """
        result = {}

        categories = [category] if category else ["cognitive", "execution", "common"]

        for cat in categories:
            cat_dir = self.prompts_dir / cat
            if cat_dir.exists():
                prompts = []
                for file in cat_dir.iterdir():
                    if file.suffix in ['.txt', '.yaml', '.yml']:
                        prompts.append(file.stem)
                if prompts:
                    result[cat] = sorted(prompts)

        return result

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self._metadata_cache.clear()
        logger.info("Prompt cache cleared")


# 전역 편의 함수
def get_prompt(prompt_name: str, variables: Dict[str, Any] = None) -> str:
    """
    프롬프트 가져오기 (전역 편의 함수)

    Args:
        prompt_name: 프롬프트 이름
        variables: 변수

    Returns:
        완성된 프롬프트
    """
    manager = PromptManager()
    return manager.get(prompt_name, variables)
