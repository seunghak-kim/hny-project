"""
LLM Service - 중앙화된 LLM 호출 관리
모든 LLM 호출을 통합 관리하여 일관성, 모니터링, 에러 핸들링 제공
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.context import LLMContext
from app.service_agent.foundation.config import Config
from app.service_agent.llm_manager.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class LLMService:
    """
    중앙화된 LLM 호출 서비스
    - OpenAI 클라이언트 관리
    - 프롬프트 기반 호출
    - 에러 핸들링 & 재시도
    - 로깅 & 모니터링
    """

    # 싱글톤 클라이언트 캐시
    _clients: Dict[str, OpenAI] = {}
    _async_clients: Dict[str, AsyncOpenAI] = {}

    def __init__(self, llm_context: LLMContext = None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트 (None이면 기본값 사용)
        """
        self.context = llm_context
        self.prompt_manager = PromptManager()

        # 클라이언트 생성 (싱글톤 패턴)
        self.client = self._get_or_create_client(sync=True)
        self.async_client = self._get_or_create_client(sync=False)

    def _get_or_create_client(self, sync: bool = True):
        """
        OpenAI 클라이언트 생성 또는 재사용 (싱글톤)

        Args:
            sync: True면 동기 클라이언트, False면 비동기 클라이언트

        Returns:
            OpenAI 또는 AsyncOpenAI 클라이언트
        """
        # API 키 가져오기
        if self.context and self.context.api_key:
            api_key = self.context.api_key
        else:
            api_key = Config.LLM_DEFAULTS.get("api_key")

        if not api_key:
            raise ValueError("OpenAI API key not found in context or config")

        # 캐시 키 생성
        cache_key = f"{api_key[:10]}_{sync}"

        # 싱글톤 패턴: 이미 생성된 클라이언트 재사용
        if sync:
            if cache_key not in self._clients:
                self._clients[cache_key] = OpenAI(api_key=api_key)
                logger.debug(f"Created new sync OpenAI client")
            return self._clients[cache_key]
        else:
            if cache_key not in self._async_clients:
                self._async_clients[cache_key] = AsyncOpenAI(api_key=api_key)
                logger.debug(f"Created new async OpenAI client")
            return self._async_clients[cache_key]

    def complete(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        response_format: Dict[str, str] = None,
        **kwargs
    ) -> str:
        """
        동기 LLM 호출 (프롬프트 기반)

        Args:
            prompt_name: 프롬프트 이름 (예: "intent_analysis")
            variables: 프롬프트 변수 (예: {"query": "전세 계약은?"})
            model: 모델 이름 (None이면 자동 선택)
            temperature: 온도 (None이면 기본값)
            max_tokens: 최대 토큰 (None이면 기본값)
            response_format: 응답 형식 (예: {"type": "json_object"})
            **kwargs: 추가 OpenAI 파라미터

        Returns:
            LLM 응답 텍스트
        """
        # 프롬프트 로드
        prompt = self.prompt_manager.get(prompt_name, variables or {})

        # 모델 선택 (Config에서 자동 선택 또는 명시적 지정)
        if model is None:
            model = Config.LLM_DEFAULTS["models"].get(prompt_name, "gpt-4o-mini")

        # 파라미터 설정
        params = {
            "model": model,
            "messages": [{"role": "system", "content": prompt}],
            "temperature": temperature or Config.LLM_DEFAULTS["default_params"]["temperature"],
            "max_tokens": max_tokens or Config.LLM_DEFAULTS["default_params"]["max_tokens"],
        }

        # Response format 설정
        if response_format:
            params["response_format"] = response_format

        # 추가 파라미터 병합
        params.update(kwargs)

        # LLM 호출 with 재시도
        try:
            response = self._call_with_retry(params)

            # 로깅
            self._log_call(prompt_name, response)

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM call failed for {prompt_name}: {e}")
            raise

    async def complete_async(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        response_format: Dict[str, str] = None,
        **kwargs
    ) -> str:
        """
        비동기 LLM 호출 (프롬프트 기반)

        Args:
            (complete 메서드와 동일)

        Returns:
            LLM 응답 텍스트
        """
        # 프롬프트 로드
        prompt = self.prompt_manager.get(prompt_name, variables or {})

        # 모델 선택
        if model is None:
            model = Config.LLM_DEFAULTS["models"].get(prompt_name, "gpt-4o-mini")

        # 파라미터 설정
        params = {
            "model": model,
            "messages": [{"role": "system", "content": prompt}],
            "temperature": temperature or Config.LLM_DEFAULTS["default_params"]["temperature"],
            "max_tokens": max_tokens or Config.LLM_DEFAULTS["default_params"]["max_tokens"],
        }

        if response_format:
            params["response_format"] = response_format

        params.update(kwargs)

        # 비동기 LLM 호출 with 재시도
        try:
            response = await self._call_async_with_retry(params)

            # 로깅
            self._log_call(prompt_name, response)

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Async LLM call failed for {prompt_name}: {e}")
            raise

    def complete_json(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        JSON 응답 LLM 호출 (동기)

        Args:
            prompt_name: 프롬프트 이름
            variables: 프롬프트 변수
            **kwargs: 추가 파라미터

        Returns:
            JSON 파싱된 응답
        """
        import json

        # JSON 모드 강제
        kwargs["response_format"] = {"type": "json_object"}

        response = self.complete(prompt_name, variables, **kwargs)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    async def complete_json_async(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        JSON 응답 LLM 호출 (비동기)

        Args:
            prompt_name: 프롬프트 이름
            variables: 프롬프트 변수
            **kwargs: 추가 파라미터

        Returns:
            JSON 파싱된 응답
        """
        import json

        # OpenAI JSON mode requirement: 프롬프트에 "JSON" 단어가 포함되어야 함
        # 프롬프트 템플릿에 이미 JSON이 포함되어 있어야 함
        kwargs["response_format"] = {"type": "json_object"}

        response = await self.complete_async(prompt_name, variables, **kwargs)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def _call_with_retry(self, params: Dict[str, Any]) -> ChatCompletion:
        """
        재시도 로직이 포함된 동기 LLM 호출

        Args:
            params: OpenAI API 파라미터

        Returns:
            ChatCompletion 응답
        """
        retry_config = Config.LLM_DEFAULTS.get("retry", {})
        max_attempts = retry_config.get("max_attempts", 3)
        backoff_seconds = retry_config.get("backoff_seconds", 1.0)

        last_error = None

        for attempt in range(max_attempts):
            try:
                return self.client.chat.completions.create(**params)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1}/{max_attempts} failed: {e}")

                if attempt < max_attempts - 1:
                    import time
                    time.sleep(backoff_seconds * (2 ** attempt))  # Exponential backoff

        raise last_error

    async def _call_async_with_retry(self, params: Dict[str, Any]) -> ChatCompletion:
        """
        재시도 로직이 포함된 비동기 LLM 호출

        Args:
            params: OpenAI API 파라미터

        Returns:
            ChatCompletion 응답
        """
        retry_config = Config.LLM_DEFAULTS.get("retry", {})
        max_attempts = retry_config.get("max_attempts", 3)
        backoff_seconds = retry_config.get("backoff_seconds", 1.0)

        last_error = None

        for attempt in range(max_attempts):
            try:
                return await self.async_client.chat.completions.create(**params)
            except Exception as e:
                last_error = e
                logger.warning(f"Async LLM call attempt {attempt + 1}/{max_attempts} failed: {e}")

                if attempt < max_attempts - 1:
                    await asyncio.sleep(backoff_seconds * (2 ** attempt))

        raise last_error

    def _log_call(self, prompt_name: str, response: ChatCompletion):
        """
        LLM 호출 로깅

        Args:
            prompt_name: 프롬프트 이름
            response: OpenAI 응답
        """
        usage = response.usage
        logger.info(
            f"LLM Call: {prompt_name} | "
            f"Model: {response.model} | "
            f"Tokens: {usage.total_tokens} "
            f"(prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})"
        )

    async def generate_final_response(
        self,
        query: str,
        aggregated_results: Dict[str, Any],
        intent_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        최종 사용자 응답 생성 (팀 결과 종합)

        Args:
            query: 사용자 질문
            aggregated_results: 팀별 수집 결과 (search, analysis, document)
            intent_info: 의도 분석 정보 (intent_type, confidence, keywords, entities)

        Returns:
            {
                "type": "answer",
                "answer": "생성된 답변",
                "teams_used": ["search", "analysis"],
                "data": {팀별 결과}
            }
        """
        import json

        # 입력 검증
        if not query:
            logger.warning("Empty query provided to generate_final_response")
            return self._generate_error_response("질문이 비어있습니다.")

        if not aggregated_results:
            logger.warning("No aggregated results provided to generate_final_response")
            return self._generate_error_response("수집된 정보가 없습니다.")

        # Intent 정보 추출
        intent_type = intent_info.get("intent_type", "알 수 없음")
        intent_confidence = intent_info.get("confidence", 0.0)
        keywords = intent_info.get("keywords", [])

        # 프롬프트 변수 구성
        try:
            # aggregated_results를 JSON으로 변환 (최대 4000자)
            aggregated_json = self._safe_json_dumps(aggregated_results)[:4000]

            # 키워드를 문자열로 변환
            keywords_str = ", ".join(keywords) if keywords else "없음"

            # 신뢰도를 퍼센트로 변환
            confidence_str = f"{intent_confidence:.0%}"

            variables = {
                "query": query,
                "intent_type": intent_type,
                "intent_confidence": confidence_str,
                "keywords": keywords_str,
                "aggregated_results": aggregated_json
            }

            # LLM 호출 (response_synthesis 프롬프트 사용) - JSON 모드로 변경
            response_json = await self.complete_json_async(
                prompt_name="response_synthesis",
                variables=variables,
                temperature=0.3,
                max_tokens=1000
            )

            logger.info(f"Final response generated successfully for query: {query[:50]}...")

            return {
                "type": "answer",
                "answer": response_json.get("answer", ""),
                "structured_data": {
                    "sections": self._create_sections(response_json, intent_info),
                    "metadata": {
                        "confidence": response_json.get("confidence", 0.8),
                        "sources": response_json.get("sources", []),
                        "intent_type": intent_info.get("intent_type", "unknown")
                    }
                },
                "teams_used": list(aggregated_results.keys()),
                "data": aggregated_results
            }

        except Exception as e:
            logger.error(f"Failed to generate final response: {e}", exc_info=True)
            return self._generate_error_response(f"응답 생성 중 오류가 발생했습니다: {str(e)}")

    def _safe_json_dumps(self, obj: Any) -> str:
        """
        객체를 안전하게 JSON 문자열로 변환 (datetime 처리 포함)

        Args:
            obj: 변환할 객체

        Returns:
            JSON 문자열
        """
        from datetime import datetime
        import json

        def json_serial(obj):
            """datetime 등 기본 JSON 직렬화 불가능한 객체 처리"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        try:
            return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to serialize object to JSON: {e}")
            return str(obj)

    def _create_sections(self, response_json: Dict[str, Any], intent_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        JSON 응답을 UI 섹션으로 변환

        Args:
            response_json: LLM이 생성한 JSON 응답
            intent_info: 의도 분석 정보

        Returns:
            UI 섹션 리스트
        """
        sections = []

        # 1. 핵심 답변 섹션
        if response_json.get("answer"):
            sections.append({
                "title": "핵심 답변",
                "content": response_json["answer"],
                "icon": "target",
                "priority": "high",
                "expandable": False  # 핵심 답변은 항상 표시
            })

        # 2. 세부 정보 섹션
        details = response_json.get("details", {})

        # 법적 근거
        if details.get("legal_basis"):
            sections.append({
                "title": "법적 근거",
                "content": details["legal_basis"],
                "icon": "scale",
                "priority": "medium",
                "expandable": True
            })

        # 데이터 분석
        if details.get("data_analysis"):
            sections.append({
                "title": "데이터 분석",
                "content": details["data_analysis"],
                "icon": "chart",
                "priority": "medium",
                "expandable": True
            })

        # 고려사항
        if details.get("considerations"):
            sections.append({
                "title": "고려사항",
                "content": details["considerations"],
                "icon": "alert",
                "type": "checklist",
                "priority": "medium",
                "expandable": True
            })

        # 3. 추천사항 섹션
        if response_json.get("recommendations"):
            sections.append({
                "title": "추천사항",
                "content": response_json["recommendations"],
                "icon": "lightbulb",
                "type": "checklist",
                "priority": "high",
                "expandable": True
            })

        # 4. 추가 정보 섹션
        if response_json.get("additional_info"):
            sections.append({
                "title": "참고사항",
                "content": response_json["additional_info"],
                "icon": "info",
                "priority": "low",
                "expandable": True
            })

        # 섹션이 없는 경우 기본 답변 섹션 생성
        if not sections and response_json.get("answer"):
            sections.append({
                "title": "답변",
                "content": response_json.get("answer", "답변을 생성할 수 없습니다."),
                "icon": "message",
                "priority": "high",
                "expandable": False
            })

        return sections

    def _generate_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        에러 응답 생성

        Args:
            error_message: 에러 메시지

        Returns:
            에러 응답 딕셔너리
        """
        return {
            "type": "error",
            "message": error_message,
            "teams_used": [],
            "data": {}
        }


# ============ 편의 함수 ============

def create_llm_service(llm_context: LLMContext = None) -> LLMService:
    """
    LLMService 인스턴스 생성 (편의 함수)

    Args:
        llm_context: LLM 컨텍스트

    Returns:
        LLMService 인스턴스
    """
    return LLMService(llm_context)
