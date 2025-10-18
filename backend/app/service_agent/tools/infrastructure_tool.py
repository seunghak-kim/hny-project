"""
Infrastructure Tool (아파트 주변 인프라 API)
에이전트가 사용하는 주변 시설 조회 도구

카카오 로컬 API 사용:
- 지하철역 검색
- 학교 검색 (초/중/고)
- 편의시설 검색 (마트, 병원, 약국 등)
- 문화시설 검색 (도서관, 문화센터 등)
"""

import logging
import os
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class InfrastructureTool:
    """
    주변 인프라 조회 Tool (카카오 API 기반)

    에이전트가 부동산 주변 시설 정보를 검색할 때 사용
    """

    # 시설 카테고리 매핑 (카카오 로컬 API 공식 카테고리 코드)
    CATEGORY_MAP = {
        # 교통
        "subway": "SW8",  # 지하철역

        # 교육 (카카오 API는 SC4만 지원, 중/고등학교는 키워드 검색 필요)
        "kindergarten": "PS3",  # 유치원
        "elementary_school": "SC4",  # 초/중/고등학교 (통합)
        "middle_school": "SC4",  # 초/중/고등학교 (통합) - 키워드 필터링
        "high_school": "SC4",  # 초/중/고등학교 (통합) - 키워드 필터링
        "academy": "AC5",  # 학원

        # 쇼핑
        "mart": "MT1",  # 대형마트
        "convenience_store": "CS2",  # 편의점

        # 의료
        "hospital": "HP8",  # 병원
        "pharmacy": "PM9",  # 약국

        # 문화/여가
        "cafe": "CE7",  # 카페

        # 공공시설
        "bank": "BK9",  # 은행
    }

    def __init__(self, kakao_api_key: Optional[str] = None):
        """
        초기화

        Args:
            kakao_api_key: 카카오 REST API 키 (None이면 환경변수에서)
        """
        load_dotenv()
        self.api_key = kakao_api_key or os.getenv("KAKAO_REST_API_KEY")

        if not self.api_key:
            logger.warning("KAKAO_REST_API_KEY not found. Infrastructure search will fail.")

        self.base_url = "https://dapi.kakao.com/v2/local/search"
        self.headers = {"Authorization": f"KakaoAK {self.api_key}"}

        logger.info("InfrastructureTool initialized successfully")

    # =========================================================================
    # Tool 메서드들 (에이전트가 호출)
    # =========================================================================

    def search(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        주변 인프라 검색 (Tool의 메인 메서드)

        Args:
            query: 검색 쿼리 (시설명 또는 위치)
            params: 검색 파라미터
                - latitude: 위도 (중심 좌표)
                - longitude: 경도 (중심 좌표)
                - category: 시설 카테고리 (subway, school, mart 등)
                - radius: 검색 반경 (미터, 기본값: 1000)
                - limit: 결과 개수 (기본값: 15)

        Returns:
            검색 결과 딕셔너리
        """
        params = params or {}

        try:
            # 파라미터 추출
            latitude = params.get("latitude")
            longitude = params.get("longitude")
            category = params.get("category", "all")
            radius = params.get("radius", 1000)
            limit = params.get("limit", 15)

            # 좌표 검증
            if not latitude or not longitude:
                return {
                    "status": "error",
                    "error": "latitude and longitude are required",
                    "data": []
                }

            # 카테고리별 검색
            if category != "all":
                results = self._search_by_category(
                    category=category,
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    limit=limit
                )
            else:
                # 전체 카테고리 검색
                results = self._search_all_categories(
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    limit=limit
                )

            return {
                "status": "success",
                "query": query,
                "count": len(results),
                "results": results,
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius
            }

        except Exception as e:
            logger.error(f"Infrastructure search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "data": []
            }

    # =========================================================================
    # 개별 시설 검색 메서드
    # =========================================================================

    def search_subway_stations(
        self,
        latitude: float,
        longitude: float,
        radius: int = 1000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        주변 지하철역 검색

        Args:
            latitude: 위도
            longitude: 경도
            radius: 검색 반경 (미터)
            limit: 결과 개수

        Returns:
            지하철역 목록
        """
        return self._search_by_category("subway", latitude, longitude, radius, limit)

    def search_schools(
        self,
        latitude: float,
        longitude: float,
        school_type: str = "elementary",
        radius: int = 1000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        주변 학교 검색

        Args:
            latitude: 위도
            longitude: 경도
            school_type: 학교 유형 (elementary, middle, high)
            radius: 검색 반경
            limit: 결과 개수

        Returns:
            학교 목록
        """
        category_map = {
            "elementary": "elementary_school",
            "middle": "middle_school",
            "high": "high_school",
        }

        category = category_map.get(school_type, "elementary_school")
        return self._search_by_category(category, latitude, longitude, radius, limit)

    def search_convenience_facilities(
        self,
        latitude: float,
        longitude: float,
        facility_type: str = "mart",
        radius: int = 500,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        주변 편의시설 검색

        Args:
            latitude: 위도
            longitude: 경도
            facility_type: 시설 유형 (mart, convenience_store, hospital, pharmacy)
            radius: 검색 반경
            limit: 결과 개수

        Returns:
            편의시설 목록
        """
        return self._search_by_category(facility_type, latitude, longitude, radius, limit)

    # =========================================================================
    # 통합 검색 메서드
    # =========================================================================

    def get_comprehensive_infrastructure(
        self,
        latitude: float,
        longitude: float,
        radius: int = 1000
    ) -> Dict[str, Any]:
        """
        종합 인프라 정보 조회 (지하철, 학교, 편의시설 등)

        Args:
            latitude: 위도
            longitude: 경도
            radius: 검색 반경

        Returns:
            카테고리별 인프라 정보
        """
        try:
            infrastructure = {
                "transportation": {
                    "subway_stations": self.search_subway_stations(latitude, longitude, radius, 5),
                },
                "education": {
                    "elementary_schools": self.search_schools(latitude, longitude, "elementary", radius, 3),
                    "middle_schools": self.search_schools(latitude, longitude, "middle", radius, 3),
                    "high_schools": self.search_schools(latitude, longitude, "high", radius, 3),
                },
                "convenience": {
                    "marts": self.search_convenience_facilities(latitude, longitude, "mart", 500, 3),
                    "hospitals": self.search_convenience_facilities(latitude, longitude, "hospital", 1000, 3),
                    "pharmacies": self.search_convenience_facilities(latitude, longitude, "pharmacy", 500, 3),
                },
            }

            # 통계 계산
            total_count = sum(
                len(facilities)
                for category in infrastructure.values()
                for facilities in category.values()
            )

            return {
                "status": "success",
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,
                "total_count": total_count,
                "infrastructure": infrastructure
            }

        except Exception as e:
            logger.error(f"Comprehensive infrastructure search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "infrastructure": {}
            }

    # =========================================================================
    # 내부 헬퍼 메서드
    # =========================================================================

    def _search_by_category(
        self,
        category: str,
        latitude: float,
        longitude: float,
        radius: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        카테고리별 검색 (내부 메서드)

        Args:
            category: 시설 카테고리
            latitude: 위도
            longitude: 경도
            radius: 검색 반경
            limit: 결과 개수

        Returns:
            검색 결과 목록
        """
        # API 키가 없으면 빈 배열 반환
        if not self.api_key:
            logger.warning(f"KAKAO_API_KEY not configured. Cannot search infrastructure.")
            return []

        try:
            # 카카오 카테고리 코드 가져오기
            category_code = self.CATEGORY_MAP.get(category)

            if not category_code:
                logger.warning(f"Unknown category: {category}")
                return []

            # API 호출
            url = f"{self.base_url}/category.json"

            # 필터링이 필요한 카테고리는 최대한 많이 가져온 후 필터링
            needs_filtering = category in ["middle_school", "high_school", "elementary_school"]
            api_size = 15 if needs_filtering else min(limit, 15)

            params = {
                "category_group_code": category_code,
                "x": longitude,
                "y": latitude,
                "radius": radius,
                "size": api_size,
                "sort": "distance"
            }

            logger.info(f"Kakao API request - Category: {category}, Code: {category_code}, Location: ({latitude}, {longitude}), Radius: {radius}")

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            documents = data.get("documents", [])

            logger.info(f"Kakao API response - Category: {category}, Found: {len(documents)} results")

            # 결과 포맷팅
            results = []
            for doc in documents:
                place_name = doc.get("place_name", "")

                # 학교 유형별 필터링 (SC4는 모든 학교를 포함하므로)
                if category == "elementary_school" and "초등학교" not in place_name:
                    continue
                if category == "middle_school" and "중학교" not in place_name:
                    continue
                if category == "high_school" and "고등학교" not in place_name:
                    continue

                results.append({
                    "name": place_name,
                    "address": doc.get("address_name", ""),
                    "road_address": doc.get("road_address_name", ""),
                    "phone": doc.get("phone", ""),
                    "category": doc.get("category_name", ""),
                    "distance": int(doc.get("distance", 0)),  # 거리 (미터)
                    "latitude": float(doc.get("y", 0)),
                    "longitude": float(doc.get("x", 0)),
                    "place_url": doc.get("place_url", ""),
                })

                # limit에 도달하면 중단
                if len(results) >= limit:
                    break

            logger.info(f"Kakao API final results - Category: {category}, After filtering: {len(results)} results")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Kakao API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return []

    def _search_all_categories(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        전체 카테고리 검색 (내부 메서드)

        Args:
            latitude: 위도
            longitude: 경도
            radius: 검색 반경
            limit: 각 카테고리당 결과 개수

        Returns:
            모든 카테고리 검색 결과
        """
        all_results = []

        # 주요 카테고리만 검색
        main_categories = ["subway", "elementary_school", "mart", "hospital", "pharmacy"]

        for category in main_categories:
            results = self._search_by_category(category, latitude, longitude, radius, limit)
            all_results.extend(results)

        return all_results


# =========================================================================
# 편의 함수
# =========================================================================

def create_infrastructure_tool(kakao_api_key: Optional[str] = None) -> InfrastructureTool:
    """
    InfrastructureTool 인스턴스 생성 헬퍼 함수

    Args:
        kakao_api_key: 카카오 REST API 키 (None이면 환경변수에서)

    Returns:
        InfrastructureTool 인스턴스
    """
    return InfrastructureTool(kakao_api_key=kakao_api_key)
