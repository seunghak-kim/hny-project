"""
RealEstateSearchTool에 캐싱 적용하는 방법 (수정 가이드)
==========================================================

이 파일은 real_estate_search_tool.py에 CacheManager를 통합하는 방법을 보여줍니다.

주요 수정 사항:
1. CacheManager import 추가
2. __init__에 cache_manager 초기화
3. search 메서드에 캐싱 로직 추가
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1단계: Import 추가 (real_estate_search_tool.py 상단에 추가)
# ============================================================================

"""
기존:
from sqlalchemy.orm import Session, joinedload

추가:
from app.core.cache_manager import get_cache_manager
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
    # 기존 DB imports
    self._ensure_db_imports()
    logger.info("RealEstateSearchTool initialized with PostgreSQL connection")

    # ⭐ NEW: CacheManager 초기화
    try:
        self.cache_manager = get_cache_manager(enabled=enable_cache)
        if self.cache_manager.enabled:
            logger.info("✅ CacheManager enabled for RealEstateSearchTool")
        else:
            logger.warning("⚠️ CacheManager disabled")
    except Exception as e:
        logger.error(f"❌ CacheManager initialization failed: {e}")
        self.cache_manager = None


# ============================================================================
# 3단계: search 메서드 수정 (캐싱 로직 추가)
# ============================================================================

async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    부동산 매물 검색 (캐싱 적용)

    캐싱 전략:
    - 캐시 키: search_type + params
    - TTL: 5분 (300초) - 매물 정보는 자주 변하므로 짧게 설정
    - 파라미터 정규화: region, property_type, price, area 등
    """
    params = params or {}

    # 파라미터 추출
    region = params.get('region') or self._extract_region(query)
    property_type = params.get('property_type')
    min_price = params.get('min_price')
    max_price = params.get('max_price')
    min_area = params.get('min_area')
    max_area = params.get('max_area')
    completion_year = params.get('completion_year')
    limit = params.get('limit', 10)
    offset = params.get('offset', 0)

    # ⭐ NEW: 캐시 키 생성 (검색 파라미터 정규화)
    cache_params = {
        "region": region,
        "property_type": property_type,
        "min_price": min_price,
        "max_price": max_price,
        "min_area": min_area,
        "max_area": max_area,
        "completion_year": completion_year,
        "limit": limit,
        "offset": offset
    }

    # ⭐ NEW: 캐시 확인
    if self.cache_manager and self.cache_manager.enabled:
        cached_results = self.cache_manager.get_search_results(
            search_type="real_estate",
            params=cache_params
        )

        if cached_results:
            logger.info(f"✅ [Cache HIT] Real estate search: {region}, {property_type}")
            # 캐시된 결과에 메타데이터 추가
            cached_results["cache_hit"] = True
            cached_results["cached_at"] = cached_results.get("cached_at", "unknown")
            return cached_results

    # 캐시 미스 → DB 쿼리 실행
    logger.info(f"❌ [Cache MISS] Real estate search: {region}, {property_type}")

    db = self.SessionLocal()
    try:
        # 기존 DB 쿼리 로직
        results = self._query_real_estates(
            db, property_name=params.get('property_name'),
            region=region,
            property_type=property_type,
            min_area=min_area,
            max_area=max_area,
            min_price=min_price,
            max_price=max_price,
            completion_year=completion_year,
            limit=limit,
            offset=offset,
            include_nearby=params.get('include_nearby', False),
            include_transactions=params.get('include_transactions', True),
            include_agent=params.get('include_agent', False)
        )

        response = {
            "status": "success",
            "data": results,
            "result_count": len(results),
            "metadata": {
                "region": region,
                "property_type": property_type,
                "filters": {
                    "min_area": min_area,
                    "max_area": max_area,
                    "min_price": min_price,
                    "max_price": max_price,
                    "completion_year": completion_year
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset
                },
                "data_source": "PostgreSQL"
            },
            "cache_hit": False,
            "cached_at": None
        }

        # ⭐ NEW: 캐시 저장
        if self.cache_manager and self.cache_manager.enabled:
            # 캐시할 때는 cached_at 추가
            from datetime import datetime
            response["cached_at"] = datetime.now().isoformat()

            self.cache_manager.cache_search_results(
                search_type="real_estate",
                params=cache_params,
                results=response,
                ttl=300  # 5분
            )
            logger.info(f"💾 [Cache SAVE] Real estate search: {region}, {property_type}")

        return response

    except Exception as e:
        logger.error(f"Real estate search failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "data": [],
            "result_count": 0
        }

    finally:
        db.close()


# ============================================================================
# 캐시 무효화 전략
# ============================================================================

"""
매물 데이터가 업데이트될 때 캐시 무효화 필요:

1. 전체 캐시 무효화:
   cache_manager.clear_cache("search:real_estate:*")

2. 특정 지역 캐시만 무효화:
   cache_manager.clear_cache("search:real_estate:*강남구*")

3. 주기적 캐시 갱신 (Cron Job):
   - 매 5분마다 자동 만료 (TTL=300)
   - 또는 데이터 업데이트 시 수동 무효화

예시:
```python
# 매물 추가/수정/삭제 후 캐시 무효화
def update_property(property_id, data):
    # DB 업데이트
    db.update(property_id, data)

    # 캐시 무효화
    cache_manager.clear_cache("search:real_estate:*")
```
"""


# ============================================================================
# 적용 방법 요약
# ============================================================================

"""
실제 real_estate_search_tool.py 수정 방법:

1. Import 추가:
   from app.core.cache_manager import get_cache_manager
   from datetime import datetime

2. __init__ 메서드에 추가:
   self.cache_manager = get_cache_manager(enabled=True)

3. search 메서드 수정:
   a. 파라미터 정규화 (cache_params 생성)
   b. DB 쿼리 전: cache_manager.get_search_results() 확인
   c. DB 쿼리 후: cache_manager.cache_search_results() 저장
   d. 응답에 cache_hit, cached_at 추가

4. 테스트:
   - 동일 검색 2회 실행 → 첫 번째는 Cache MISS, 두 번째는 Cache HIT
   - 5분 후 재검색 → Cache MISS (TTL 만료)
   - 다른 파라미터로 검색 → Cache MISS

예상 효과:
- DB 쿼리: 50-70% 감소
- 응답 시간: 0.36s → 0.01s (캐시 히트 시)
- DB 부하: 50-70% 감소
"""


# ============================================================================
# TTL 설정 가이드
# ============================================================================

"""
매물 검색 TTL: 300초 (5분)
- 이유: 매물 정보는 자주 변하지 않지만, 최신 정보 제공 필요
- 트레이드오프: 짧으면 캐시 효과 감소, 길면 stale data

시세 조회 TTL: 1800초 (30분)
- 이유: 시세는 하루에 몇 번만 업데이트됨
- 더 긴 TTL 가능

법률 검색 TTL: 3600초 (1시간)
- 이유: 법률 정보는 거의 변하지 않음
- 더 긴 TTL 가능 (예: 86400초 = 24시간)

API 응답 TTL: 86400초 (24시간)
- 이유: 인프라, 건축물 대장 등은 거의 변하지 않음
- 매우 긴 TTL 적합

TTL 튜닝:
- 캐시 히트율 모니터링 (Prometheus)
- Stale data 발생 빈도 추적
- 사용자 피드백 반영
"""
