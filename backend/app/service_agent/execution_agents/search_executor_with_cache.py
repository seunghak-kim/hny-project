"""
SearchExecutor에 캐싱 적용하는 방법 (수정 가이드)
===================================================

이 파일은 search_executor.py에 CacheManager를 통합하는 방법을 보여줍니다.
실제 적용 시에는 search_executor.py를 직접 수정하세요.

주요 수정 사항:
1. CacheManager import 추가
2. __init__에 cache_manager 초기화
3. _select_tools_with_llm에 캐싱 로직 추가
4. _extract_parameters_with_llm에 캐싱 로직 추가
5. _extract_keywords_with_llm에 캐싱 로직 추가
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# 1단계: Import 추가 (search_executor.py 상단에 추가)
# ============================================================================

"""
기존:
from app.service_agent.llm_manager import LLMService

추가:
from app.core.cache_manager import get_cache_manager
"""


# ============================================================================
# 2단계: __init__ 수정 (CacheManager 초기화)
# ============================================================================

def __init__(self, llm_context=None, progress_callback=None, enable_cache=True):
    """
    초기화 (캐싱 추가)

    Args:
        llm_context: LLM 컨텍스트
        progress_callback: 진행 상황 콜백
        enable_cache: 캐싱 활성화 여부 (기본 True)
    """
    # 기존 코드...
    self.llm_context = llm_context
    self.progress_callback = progress_callback

    # LLMService 초기화
    try:
        self.llm_service = LLMService(llm_context=llm_context)
        logger.info("✅ LLMService initialized successfully")
    except Exception as e:
        logger.error(f"❌ LLMService initialization failed: {e}")
        self.llm_service = None

    # ⭐ NEW: CacheManager 초기화
    try:
        self.cache_manager = get_cache_manager(enabled=enable_cache)
        if self.cache_manager.enabled:
            logger.info("✅ CacheManager enabled")
        else:
            logger.warning("⚠️ CacheManager disabled (Redis not available or disabled)")
    except Exception as e:
        logger.error(f"❌ CacheManager initialization failed: {e}")
        self.cache_manager = None

    # 기존 코드 계속...


# ============================================================================
# 3단계: _select_tools_with_llm 수정 (캐싱 로직 추가)
# ============================================================================

async def _select_tools_with_llm(self, query: str, keywords=None) -> Dict[str, Any]:
    """
    LLM을 사용한 tool 선택 (캐싱 적용)

    캐싱 전략:
    - 캐시 키: query + available_tools
    - TTL: 1시간 (3600초)
    - 모델별 별도 캐싱
    """
    if not self.llm_service:
        logger.warning("LLM service not available, using fallback")
        return self._select_tools_with_fallback(keywords=keywords, query=query)

    try:
        # 사용 가능한 도구 목록
        available_tools = self._get_available_tools()

        # ⭐ NEW: 캐시 확인
        if self.cache_manager and self.cache_manager.enabled:
            cache_key_data = {
                "query": query,
                "available_tools": list(available_tools.keys())
            }
            cached_response = self.cache_manager.get_llm_response(
                query=str(cache_key_data),
                model="gpt-4o-mini",  # 또는 실제 사용 모델
                prompt_type="tool_selection"
            )

            if cached_response:
                logger.info(f"✅ [Cache HIT] Tool selection for: {query[:50]}...")
                return cached_response

        # 캐시 미스 또는 캐시 비활성화 → LLM 호출
        logger.info(f"❌ [Cache MISS] Tool selection for: {query[:50]}...")

        # 기존 LLM 호출 로직
        prompt = self._create_tool_selection_prompt(query, available_tools)

        response = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=500
        )

        # 응답 파싱
        selected_tools, reasoning, confidence = self._parse_tool_selection_response(response)

        result = {
            "selected_tools": selected_tools,
            "reasoning": reasoning,
            "confidence": confidence,
            "decision_id": None  # Decision logger에서 설정
        }

        # ⭐ NEW: 캐시 저장
        if self.cache_manager and self.cache_manager.enabled:
            self.cache_manager.cache_llm_response(
                query=str(cache_key_data),
                model="gpt-4o-mini",
                response=result,
                prompt_type="tool_selection",
                ttl=3600  # 1시간
            )
            logger.info(f"💾 [Cache SAVE] Tool selection for: {query[:50]}...")

        return result

    except Exception as e:
        logger.error(f"Tool selection with LLM failed: {e}", exc_info=True)
        return self._select_tools_with_fallback(keywords=keywords, query=query)


# ============================================================================
# 4단계: _extract_parameters_with_llm 수정 (캐싱 로직 추가)
# ============================================================================

async def _extract_parameters_with_llm(
    self,
    query: str,
    tool_name: str
) -> Dict[str, Any]:
    """
    LLM을 사용한 파라미터 추출 (캐싱 적용)

    캐싱 전략:
    - 캐시 키: query + tool_name
    - TTL: 1시간
    """
    if not self.llm_service:
        logger.warning("LLM service not available for parameter extraction")
        return {}

    try:
        # ⭐ NEW: 캐시 확인
        if self.cache_manager and self.cache_manager.enabled:
            cache_key_data = {
                "query": query,
                "tool_name": tool_name
            }
            cached_response = self.cache_manager.get_llm_response(
                query=str(cache_key_data),
                model="gpt-4o-mini",
                prompt_type="parameter_extraction"
            )

            if cached_response:
                logger.info(f"✅ [Cache HIT] Parameter extraction for: {tool_name}")
                return cached_response

        # 캐시 미스 → LLM 호출
        logger.info(f"❌ [Cache MISS] Parameter extraction for: {tool_name}")

        # 기존 LLM 호출 로직
        prompt = self._create_parameter_extraction_prompt(query, tool_name)

        response = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=300
        )

        # 응답 파싱
        params = self._parse_parameter_response(response, tool_name)

        # ⭐ NEW: 캐시 저장
        if self.cache_manager and self.cache_manager.enabled:
            self.cache_manager.cache_llm_response(
                query=str(cache_key_data),
                model="gpt-4o-mini",
                response=params,
                prompt_type="parameter_extraction",
                ttl=3600
            )
            logger.info(f"💾 [Cache SAVE] Parameter extraction for: {tool_name}")

        return params

    except Exception as e:
        logger.error(f"Parameter extraction failed: {e}", exc_info=True)
        return {}


# ============================================================================
# 5단계: _extract_keywords_with_llm 수정 (캐싱 로직 추가)
# ============================================================================

async def _extract_keywords_with_llm(self, query: str) -> SearchKeywords:
    """
    LLM을 사용한 키워드 추출 (캐싱 적용)

    캐싱 전략:
    - 캐시 키: query
    - TTL: 1시간
    """
    if not self.llm_service:
        logger.warning("LLM service not available for keyword extraction")
        return self._extract_keywords_with_fallback(query)

    try:
        # ⭐ NEW: 캐시 확인
        if self.cache_manager and self.cache_manager.enabled:
            cached_response = self.cache_manager.get_llm_response(
                query=query,
                model="gpt-4o-mini",
                prompt_type="keyword_extraction"
            )

            if cached_response:
                logger.info(f"✅ [Cache HIT] Keyword extraction for: {query[:50]}...")
                return SearchKeywords(**cached_response)

        # 캐시 미스 → LLM 호출
        logger.info(f"❌ [Cache MISS] Keyword extraction for: {query[:50]}...")

        # 기존 LLM 호출 로직
        prompt = self._create_keyword_extraction_prompt(query)

        response = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=200
        )

        # 응답 파싱
        keywords = self._parse_keyword_response(response)

        # ⭐ NEW: 캐시 저장
        if self.cache_manager and self.cache_manager.enabled:
            # SearchKeywords 객체를 dict로 변환
            keywords_dict = {
                "legal": keywords.legal,
                "real_estate": keywords.real_estate,
                "loan": keywords.loan,
                "general": keywords.general
            }

            self.cache_manager.cache_llm_response(
                query=query,
                model="gpt-4o-mini",
                response=keywords_dict,
                prompt_type="keyword_extraction",
                ttl=3600
            )
            logger.info(f"💾 [Cache SAVE] Keyword extraction for: {query[:50]}...")

        return keywords

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}", exc_info=True)
        return self._extract_keywords_with_fallback(query)


# ============================================================================
# 적용 방법 요약
# ============================================================================

"""
실제 search_executor.py 수정 방법:

1. Import 추가:
   from app.core.cache_manager import get_cache_manager

2. __init__ 메서드에 추가:
   self.cache_manager = get_cache_manager(enabled=True)

3. _select_tools_with_llm 메서드 수정:
   - LLM 호출 전: cache_manager.get_llm_response() 확인
   - LLM 호출 후: cache_manager.cache_llm_response() 저장

4. _extract_parameters_with_llm 메서드 수정:
   - 동일한 패턴 적용

5. _extract_keywords_with_llm 메서드 수정:
   - 동일한 패턴 적용

6. 테스트:
   - Redis 없이 테스트 (enabled=False)
   - Redis 있을 때 테스트 (캐시 히트/미스 로그 확인)
   - 성능 측정 (응답 시간, 비용)

예상 효과:
- 응답 시간: 7.05s → 2.5-3.5s (50% 단축)
- LLM 비용: 50-70% 절감
- 캐시 히트율: 55-70% (트래픽에 따라)
"""


# ============================================================================
# Redis 설치 및 실행 방법
# ============================================================================

"""
Redis 설치 (macOS):
```bash
# Homebrew로 설치
brew install redis

# Redis 시작
brew services start redis

# Redis 확인
redis-cli ping
# 응답: PONG

# Redis 중지
brew services stop redis
```

Redis 설치 (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install redis-server

# Redis 시작
sudo systemctl start redis-server

# Redis 확인
redis-cli ping
```

Python Redis 라이브러리 설치:
```bash
pip install redis
```

Redis 없이 테스트:
```python
# CacheManager는 Redis 연결 실패 시 자동으로 비활성화됨
cache = CacheManager(enabled=True)  # Redis 없어도 동작
```
"""
