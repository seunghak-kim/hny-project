"""
InfrastructureTool에 API 응답 캐싱 적용하는 방법 (수정 가이드)
===================================================================

외부 API 응답 캐싱 (인프라, 건축물 대장 등)

주요 수정 사항:
1. CacheManager import 추가
2. __init__에 cache_manager 초기화
3. search 메서드에 API 캐싱 로직 추가
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1단계: Import 추가 (infrastructure_tool.py 상단에 추가)
# ============================================================================

"""
추가:
from app.core.cache_manager import get_cache_manager
from datetime import datetime
"""


# ============================================================================
# 2단계: __init__ 수정 (CacheManager 초기화)
# ============================================================================

def __init__(self, enable_cache=True):
    """
    초기화 (캐싱 추가)

    Args:
        enable_cache: 캐싱 활성화 여부 (기본 True)
    """
    # ⭐ NEW: CacheManager 초기화
    try:
        self.cache_manager = get_cache_manager(enabled=enable_cache)
        if self.cache_manager.enabled:
            logger.info("✅ CacheManager enabled for InfrastructureTool")
        else:
            logger.warning("⚠️ CacheManager disabled")
    except Exception as e:
        logger.error(f"❌ CacheManager initialization failed: {e}")
        self.cache_manager = None


# ============================================================================
# 3단계: search 메서드 수정 (API 캐싱 로직 추가)
# ============================================================================

async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    인프라 검색 (API 캐싱 적용)

    캐싱 전략:
    - 캐시 키: api_name + request_params (region, radius 등)
    - TTL: 24시간 (86400초) - 인프라 정보는 거의 변하지 않음
    """
    params = params or {}

    # 파라미터 추출
    region = params.get('region') or self._extract_region(query)
    radius = params.get('radius', 500)
    facility_type = params.get('facility_type', 'all')  # subway, school, park, etc.

    # ⭐ NEW: API 요청 파라미터 (캐시 키용)
    api_request_params = {
        "region": region,
        "radius": radius,
        "facility_type": facility_type
    }

    # ⭐ NEW: 캐시 확인
    if self.cache_manager and self.cache_manager.enabled:
        cached_response = self.cache_manager.get_api_response(
            api_name="infrastructure",
            request_params=api_request_params
        )

        if cached_response:
            logger.info(f"✅ [Cache HIT] Infrastructure API: {region}, radius={radius}")
            # 캐시된 응답에 메타데이터 추가
            cached_response["cache_hit"] = True
            cached_response["cached_at"] = cached_response.get("cached_at", "unknown")
            return cached_response

    # 캐시 미스 → API 호출
    logger.info(f"❌ [Cache MISS] Infrastructure API: {region}, radius={radius}")

    try:
        # 기존 외부 API 호출 로직
        # 예: 카카오맵 API, 공공데이터포털 API 등
        api_results = await self._call_external_api(region, radius, facility_type)

        response = {
            "status": "success",
            "data": api_results,
            "result_count": len(api_results),
            "metadata": {
                "region": region,
                "radius": radius,
                "facility_type": facility_type,
                "data_source": "External API"
            },
            "cache_hit": False,
            "cached_at": None
        }

        # ⭐ NEW: 캐시 저장
        if self.cache_manager and self.cache_manager.enabled:
            from datetime import datetime
            response["cached_at"] = datetime.now().isoformat()

            self.cache_manager.cache_api_response(
                api_name="infrastructure",
                request_params=api_request_params,
                response=response,
                ttl=86400  # 24시간
            )
            logger.info(f"💾 [Cache SAVE] Infrastructure API: {region}, radius={radius}")

        return response

    except Exception as e:
        logger.error(f"Infrastructure API call failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "data": [],
            "result_count": 0
        }


async def _call_external_api(
    self,
    region: str,
    radius: int,
    facility_type: str
) -> list:
    """
    외부 API 호출 (실제 구현)

    예: 카카오맵 API로 주변 시설 검색
    """
    # 실제 API 호출 로직
    # ...
    pass


# ============================================================================
# BuildingRegistryTool 캐싱 (유사한 패턴)
# ============================================================================

class BuildingRegistryToolWithCache:
    """건축물 대장 API 캐싱 적용"""

    def __init__(self, enable_cache=True):
        self.cache_manager = get_cache_manager(enabled=enable_cache)

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        건축물 대장 조회 (API 캐싱)

        캐시 전략:
        - TTL: 24시간 (건축물 정보는 거의 변하지 않음)
        """
        params = params or {}

        # 파라미터 추출
        address = params.get('address')
        building_name = params.get('building_name')

        api_request_params = {
            "address": address,
            "building_name": building_name
        }

        # 캐시 확인
        if self.cache_manager and self.cache_manager.enabled:
            cached_response = self.cache_manager.get_api_response(
                api_name="building_registry",
                request_params=api_request_params
            )

            if cached_response:
                logger.info(f"✅ [Cache HIT] Building Registry API: {address}")
                cached_response["cache_hit"] = True
                return cached_response

        # API 호출
        logger.info(f"❌ [Cache MISS] Building Registry API: {address}")

        try:
            api_results = await self._call_building_api(address, building_name)

            response = {
                "status": "success",
                "data": api_results,
                "result_count": len(api_results),
                "cache_hit": False
            }

            # 캐시 저장
            if self.cache_manager and self.cache_manager.enabled:
                from datetime import datetime
                response["cached_at"] = datetime.now().isoformat()

                self.cache_manager.cache_api_response(
                    api_name="building_registry",
                    request_params=api_request_params,
                    response=response,
                    ttl=86400  # 24시간
                )
                logger.info(f"💾 [Cache SAVE] Building Registry API: {address}")

            return response

        except Exception as e:
            logger.error(f"Building Registry API failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": [],
                "result_count": 0
            }


# ============================================================================
# 적용 방법 요약
# ============================================================================

"""
실제 infrastructure_tool.py 및 building_registry_tool.py 수정 방법:

1. Import 추가:
   from app.core.cache_manager import get_cache_manager
   from datetime import datetime

2. __init__ 메서드에 추가:
   self.cache_manager = get_cache_manager(enabled=True)

3. search 메서드 수정:
   a. API 요청 파라미터 정규화
   b. API 호출 전: cache_manager.get_api_response() 확인
   c. API 호출 후: cache_manager.cache_api_response() 저장
   d. TTL: 24시간 (86400초)

4. 테스트:
   - 동일 API 요청 2회 → 첫 번째는 Cache MISS, 두 번째는 Cache HIT
   - API 호출 시간: 500-1500ms → 캐시 히트 시 5-10ms

예상 효과:
- API 호출: 50-70% 감소
- 응답 시간: 0.5-1.5s → 0.01s (캐시 히트 시)
- API 비용: 50-70% 절감 (API 호출 횟수 제한 있는 경우)
- 외부 서비스 부하: 50-70% 감소
"""


# ============================================================================
# TTL 설정 전략
# ============================================================================

"""
API 종류별 TTL 권장 사항:

1. 인프라 정보 (지하철역, 학교, 공원 등):
   - TTL: 86400초 (24시간) ~ 604800초 (7일)
   - 이유: 거의 변하지 않음

2. 건축물 대장:
   - TTL: 86400초 (24시간) ~ 2592000초 (30일)
   - 이유: 건축물 정보는 매우 안정적

3. 실시간 교통 정보:
   - TTL: 300초 (5분) ~ 900초 (15분)
   - 이유: 자주 변함

4. 날씨 정보:
   - TTL: 1800초 (30분) ~ 3600초 (1시간)
   - 이유: 시간별로 변함

TTL 튜닝 방법:
1. 모니터링: 캐시 히트율 추적
2. A/B 테스트: 다른 TTL 값 비교
3. 사용자 피드백: Stale data 발생 빈도
4. 비용 분석: API 호출 횟수 vs 캐시 스토리지 비용
"""


# ============================================================================
# 캐시 무효화 전략
# ============================================================================

"""
API 캐시 무효화가 필요한 경우:

1. 수동 무효화:
   - 데이터 업데이트 시
   - 예: 새로운 지하철역 개통
   ```python
   cache_manager.clear_cache("api:infrastructure:*강남*")
   ```

2. 주기적 갱신:
   - Cron Job으로 매일 자정 캐시 초기화
   ```bash
   0 0 * * * redis-cli FLUSHDB
   ```

3. 선택적 무효화:
   - 특정 지역만 무효화
   ```python
   cache_manager.invalidate_query_cache("강남구")
   ```

4. 이벤트 기반 무효화:
   - 외부 API에서 webhook으로 업데이트 알림 받을 때
   - 즉시 해당 캐시 삭제
"""
