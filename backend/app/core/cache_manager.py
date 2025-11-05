"""
Cache Manager - Redis 기반 캐싱 시스템
=====================================

LLM 응답, 검색 결과, API 응답 등을 캐싱하여 성능 개선 및 비용 절감

주요 기능:
1. LLM 응답 캐싱 (도구 선택, 파라미터 추출, 키워드 추출)
2. 검색 결과 캐싱 (매물 검색, 시세 조회 등)
3. 외부 API 응답 캐싱 (인프라, 건축물 대장)
4. Vector 임베딩 캐싱

예상 효과:
- 응답 시간: 50-60% 단축
- 비용: 50-70% 절감
- 캐시 히트율: 55-70%
"""

import redis
import hashlib
import json
import pickle
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 기반 캐시 관리자"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호 (있는 경우)
            enabled: 캐싱 활성화 여부 (False면 캐싱 스킵)
        """
        self.enabled = enabled

        if not enabled:
            logger.warning("⚠️ CacheManager is DISABLED. All cache operations will be skipped.")
            self.redis_client = None
            return

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # Binary 데이터 지원 (pickle)
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 연결 테스트
            self.redis_client.ping()
            logger.info(f"✅ Redis connected: {host}:{port} (DB {db})")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️ Falling back to NO CACHE mode")
            self.redis_client = None
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e}")
            self.redis_client = None
            self.enabled = False

    def _generate_cache_key(self, prefix: str, data: Union[str, Dict, tuple]) -> str:
        """
        캐시 키 생성 (해시 기반)

        Args:
            prefix: 키 접두사 (예: "llm", "search", "api")
            data: 해시할 데이터

        Returns:
            캐시 키 (예: "llm:a3f5b2c1...")
        """
        if isinstance(data, str):
            hash_input = data
        elif isinstance(data, dict):
            # Dict를 정렬하여 일관된 해시 생성
            hash_input = str(sorted(data.items()))
        elif isinstance(data, tuple):
            hash_input = str(data)
        else:
            hash_input = str(data)

        hash_digest = hashlib.md5(hash_input.encode()).hexdigest()
        return f"{prefix}:{hash_digest}"

    def _serialize(self, data: Any) -> bytes:
        """데이터 직렬화 (pickle 사용)"""
        return pickle.dumps(data)

    def _deserialize(self, data: bytes) -> Any:
        """데이터 역직렬화"""
        return pickle.loads(data)

    # ========================================================================
    # LLM 응답 캐싱
    # ========================================================================

    def get_llm_response(
        self,
        query: str,
        model: str,
        prompt_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        LLM 응답 조회

        Args:
            query: 사용자 쿼리
            model: LLM 모델명 (예: "gpt-4o-mini")
            prompt_type: 프롬프트 타입 (예: "tool_selection", "parameter_extraction")

        Returns:
            캐시된 응답 또는 None
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(
                f"llm:{model}:{prompt_type}",
                query
            )
            cached = self.redis_client.get(cache_key)

            if cached:
                result = self._deserialize(cached)
                logger.info(f"✅ LLM Cache HIT: {prompt_type} - {query[:50]}...")
                return result

            logger.debug(f"❌ LLM Cache MISS: {prompt_type} - {query[:50]}...")
            return None

        except Exception as e:
            logger.error(f"❌ LLM cache get error: {e}")
            return None

    def cache_llm_response(
        self,
        query: str,
        model: str,
        response: Dict[str, Any],
        prompt_type: str = "general",
        ttl: int = 3600
    ) -> bool:
        """
        LLM 응답 저장

        Args:
            query: 사용자 쿼리
            model: LLM 모델명
            response: LLM 응답 (Dict)
            prompt_type: 프롬프트 타입
            ttl: Time To Live (초) - 기본 1시간

        Returns:
            저장 성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(
                f"llm:{model}:{prompt_type}",
                query
            )
            serialized = self._serialize(response)
            self.redis_client.setex(cache_key, ttl, serialized)

            logger.info(f"💾 LLM Cache SAVE: {prompt_type} - {query[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ LLM cache set error: {e}")
            return False

    # ========================================================================
    # 검색 결과 캐싱
    # ========================================================================

    def get_search_results(
        self,
        search_type: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        검색 결과 조회

        Args:
            search_type: 검색 타입 (예: "real_estate", "market_data", "legal")
            params: 검색 파라미터 (Dict)

        Returns:
            캐시된 검색 결과 또는 None
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(f"search:{search_type}", params)
            cached = self.redis_client.get(cache_key)

            if cached:
                result = self._deserialize(cached)
                logger.info(f"✅ Search Cache HIT: {search_type} - {params}")
                return result

            logger.debug(f"❌ Search Cache MISS: {search_type} - {params}")
            return None

        except Exception as e:
            logger.error(f"❌ Search cache get error: {e}")
            return None

    def cache_search_results(
        self,
        search_type: str,
        params: Dict[str, Any],
        results: Dict[str, Any],
        ttl: int = 300
    ) -> bool:
        """
        검색 결과 저장

        Args:
            search_type: 검색 타입
            params: 검색 파라미터
            results: 검색 결과
            ttl: Time To Live (초) - 기본 5분

        Returns:
            저장 성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(f"search:{search_type}", params)
            serialized = self._serialize(results)
            self.redis_client.setex(cache_key, ttl, serialized)

            logger.info(f"💾 Search Cache SAVE: {search_type} - {params} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Search cache set error: {e}")
            return False

    # ========================================================================
    # 외부 API 응답 캐싱
    # ========================================================================

    def get_api_response(
        self,
        api_name: str,
        request_params: Union[str, Dict, tuple]
    ) -> Optional[Dict[str, Any]]:
        """
        외부 API 응답 조회

        Args:
            api_name: API 이름 (예: "infrastructure", "building_registry")
            request_params: API 요청 파라미터

        Returns:
            캐시된 API 응답 또는 None
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(f"api:{api_name}", request_params)
            cached = self.redis_client.get(cache_key)

            if cached:
                result = self._deserialize(cached)
                logger.info(f"✅ API Cache HIT: {api_name} - {request_params}")
                return result

            logger.debug(f"❌ API Cache MISS: {api_name} - {request_params}")
            return None

        except Exception as e:
            logger.error(f"❌ API cache get error: {e}")
            return None

    def cache_api_response(
        self,
        api_name: str,
        request_params: Union[str, Dict, tuple],
        response: Dict[str, Any],
        ttl: int = 86400
    ) -> bool:
        """
        외부 API 응답 저장

        Args:
            api_name: API 이름
            request_params: API 요청 파라미터
            response: API 응답
            ttl: Time To Live (초) - 기본 24시간

        Returns:
            저장 성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(f"api:{api_name}", request_params)
            serialized = self._serialize(response)
            self.redis_client.setex(cache_key, ttl, serialized)

            logger.info(f"💾 API Cache SAVE: {api_name} - {request_params} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ API cache set error: {e}")
            return False

    # ========================================================================
    # Vector 임베딩 캐싱
    # ========================================================================

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Vector 임베딩 조회

        Args:
            text: 임베딩할 텍스트

        Returns:
            캐시된 임베딩 (numpy array) 또는 None
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key("embedding", text)
            cached = self.redis_client.get(cache_key)

            if cached:
                embedding = self._deserialize(cached)
                logger.info(f"✅ Embedding Cache HIT: {text[:50]}...")
                return embedding

            logger.debug(f"❌ Embedding Cache MISS: {text[:50]}...")
            return None

        except Exception as e:
            logger.error(f"❌ Embedding cache get error: {e}")
            return None

    def cache_embedding(
        self,
        text: str,
        embedding: np.ndarray,
        ttl: int = 3600
    ) -> bool:
        """
        Vector 임베딩 저장

        Args:
            text: 임베딩 텍스트
            embedding: 임베딩 벡터 (numpy array)
            ttl: Time To Live (초) - 기본 1시간

        Returns:
            저장 성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key("embedding", text)
            serialized = self._serialize(embedding)
            self.redis_client.setex(cache_key, ttl, serialized)

            logger.info(f"💾 Embedding Cache SAVE: {text[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Embedding cache set error: {e}")
            return False

    # ========================================================================
    # 캐시 통계 및 관리
    # ========================================================================

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 통계 정보
        """
        if not self.enabled or not self.redis_client:
            return {"enabled": False, "message": "Cache is disabled"}

        try:
            info = self.redis_client.info()
            return {
                "enabled": True,
                "connected": True,
                "total_keys": self.redis_client.dbsize(),
                "memory_used_mb": info.get("used_memory", 0) / (1024 * 1024),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"❌ Cache stats error: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}

    def _calculate_hit_rate(self, info: Dict) -> float:
        """캐시 히트율 계산"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        캐시 삭제

        Args:
            pattern: 삭제할 키 패턴 (예: "llm:*", "search:*")
                    None이면 모든 캐시 삭제

        Returns:
            삭제된 키 개수
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    logger.info(f"🗑️ Cleared {deleted} cache keys matching: {pattern}")
                    return deleted
                return 0
            else:
                # 모든 DB 초기화
                self.redis_client.flushdb()
                logger.warning("🗑️ Cleared ALL cache (flushdb)")
                return -1

        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
            return 0

    def invalidate_query_cache(self, query: str) -> int:
        """
        특정 쿼리 관련 모든 캐시 무효화

        Args:
            query: 쿼리 문자열

        Returns:
            삭제된 키 개수
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            pattern = f"*{query_hash}*"
            return self.clear_cache(pattern)

        except Exception as e:
            logger.error(f"❌ Cache invalidation error: {e}")
            return 0


# ============================================================================
# 싱글톤 인스턴스
# ============================================================================

_cache_manager_instance: Optional[CacheManager] = None


def get_cache_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    enabled: bool = True
) -> CacheManager:
    """
    CacheManager 싱글톤 인스턴스 반환

    Args:
        host: Redis 호스트
        port: Redis 포트
        db: Redis DB 번호
        enabled: 캐싱 활성화 여부

    Returns:
        CacheManager 인스턴스
    """
    global _cache_manager_instance

    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager(
            host=host,
            port=port,
            db=db,
            enabled=enabled
        )

    return _cache_manager_instance


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)

    # CacheManager 초기화 (Redis 없어도 동작)
    cache = CacheManager(enabled=True)

    # LLM 응답 캐싱 예시
    query = "강남구 아파트 시세"
    model = "gpt-4o-mini"

    # 1. 캐시 조회
    cached_response = cache.get_llm_response(query, model, "tool_selection")
    if cached_response:
        print(f"✅ Cache hit: {cached_response}")
    else:
        # 2. LLM 호출 (실제로는 여기서 OpenAI API 호출)
        llm_response = {"tools": ["real_estate_search"], "confidence": 0.95}

        # 3. 캐시 저장
        cache.cache_llm_response(query, model, llm_response, "tool_selection", ttl=3600)

    # 통계 확인
    stats = cache.get_cache_stats()
    print(f"\n📊 Cache Stats: {stats}")
