"""
Building Registry Tool (건축물대장 API)
에이전트가 사용하는 건축물대장 조회 도구

국토부 건축HUB API 사용:
- 건축물대장 표제부 정보
- 건축물대장 총괄표제부 정보
- 층별 정보
- 동별 정보
- 호별 정보
"""

import logging
import re
from typing import Dict, Any, List, Optional

from app.utils.building_api import BuildingHubAPI, ResponseFormat, ValidationError, APIHelper, RegionCodeManager

logger = logging.getLogger(__name__)


class BuildingRegistryTool:
    """
    건축물대장 조회 Tool

    에이전트가 건축물 상세 정보를 검색할 때 사용
    """

    def __init__(self, service_key: Optional[str] = None):
        """
        초기화

        Args:
            service_key: 공공데이터 포털 Service Key (None이면 환경변수에서)
        """
        try:
            self.api = BuildingHubAPI(
                service_key=service_key,
                response_format=ResponseFormat.JSON  # JSON 형식 사용
            )
            self.region_manager = RegionCodeManager()
            logger.info("BuildingRegistryTool initialized successfully")
        except Exception as e:
            logger.error(f"BuildingRegistryTool initialization failed: {e}")
            raise

    # =========================================================================
    # Tool 메서드들 (에이전트가 호출)
    # =========================================================================

    def search(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        건축물대장 검색 (Tool의 메인 메서드)

        Args:
            query: 검색 쿼리 (주소 정보 포함)
            params: 검색 파라미터
                - sigungu_code: 시군구코드 (5자리)
                - bdong_code: 법정동코드 (5자리)
                - bun: 번지 (본번)
                - ji: 번지 (부번)
                - plat_gb_cd: 대지구분코드 (0: 대지, 1: 산, 2: 블록)
                - info_type: 조회 유형 (basic, summary, floor, dong, ho)
                - limit: 결과 개수 (기본값: 10)

        Returns:
            검색 결과 딕셔너리
        """
        params = params or {}

        try:
            # 파라미터 추출
            sigungu_code = params.get("sigungu_code")
            bdong_code = params.get("bdong_code")
            bun = params.get("bun", "")
            ji = params.get("ji", "")
            plat_gb_cd = params.get("plat_gb_cd", "0")
            info_type = params.get("info_type", "basic")
            limit = params.get("limit", 10)

            # 필수 파라미터 검증
            if not sigungu_code:
                return {
                    "status": "error",
                    "error": "sigungu_code is required (5-digit code)",
                    "data": []
                }

            if not bdong_code:
                return {
                    "status": "error",
                    "error": "bdong_code is required (5-digit code)",
                    "data": []
                }

            # API 호출
            result = self._get_building_info(
                info_type=info_type,
                sigungu_code=sigungu_code,
                bdong_code=bdong_code,
                plat_gb_cd=plat_gb_cd,
                bun=bun,
                ji=ji,
                num_of_rows=str(limit)
            )

            return {
                "status": "success" if result["success"] else "error",
                "query": query,
                "count": len(result.get("data", [])),
                "results": result.get("data", []),
                "page_info": result.get("page_info", {}),
                "info_type": info_type,
                "error": result.get("error") if not result["success"] else None
            }

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "data": []
            }
        except Exception as e:
            logger.error(f"Building registry search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "data": []
            }

    # =========================================================================
    # 개별 API 메서드 (직접 호출 가능)
    # =========================================================================

    def get_basic_info(
        self,
        sigungu_code: str,
        bdong_code: str,
        bun: str = "",
        ji: str = "",
        plat_gb_cd: str = "0",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        건축물대장 표제부 기본 정보 조회

        Args:
            sigungu_code: 시군구코드 (5자리)
            bdong_code: 법정동코드 (5자리)
            bun: 번지 (본번)
            ji: 번지 (부번)
            plat_gb_cd: 대지구분코드
            limit: 결과 개수

        Returns:
            건축물 기본 정보
        """
        return self.api.get_building_info(
            sigungu_cd=sigungu_code,
            bjdong_cd=bdong_code,
            plat_gb_cd=plat_gb_cd,
            bun=bun,
            ji=ji,
            num_of_rows=str(limit)
        )

    def get_summary_info(
        self,
        sigungu_code: str,
        bdong_code: str,
        bun: str = "",
        ji: str = "",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        건축물대장 총괄표제부 정보 조회

        Args:
            sigungu_code: 시군구코드
            bdong_code: 법정동코드
            bun: 번지 (본번)
            ji: 번지 (부번)
            limit: 결과 개수

        Returns:
            건축물 총괄 정보
        """
        # Note: 실제 API endpoint가 다를 수 있음
        # building_summary endpoint 사용 필요 시 API 클래스 확장 필요
        return self.get_basic_info(sigungu_code, bdong_code, bun, ji, "0", limit)

    def search_by_address(
        self,
        address: str,
        info_type: str = "basic",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        주소로 건축물 검색 (지역코드 자동 변환)

        Args:
            address: 주소 (예: "서울시 강남구 역삼동 123-45")
            info_type: 조회 유형
            limit: 결과 개수

        Returns:
            검색 결과
        """
        try:
            # 주소 파싱
            parsed = self._parse_address(address)

            if not parsed["success"]:
                return {
                    "status": "error",
                    "error": parsed["error"],
                    "address": address,
                    "data": []
                }

            # 지역 코드 조회
            try:
                region_info = self.region_manager.get_region_codes(
                    sigungu_name=parsed["sigungu"],
                    bdong_name=parsed["bdong"]
                )
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"지역 코드 조회 실패: {str(e)}",
                    "address": address,
                    "parsed": parsed,
                    "data": []
                }

            # API 호출
            result = self._get_building_info(
                info_type=info_type,
                sigungu_code=region_info["sigungu_code"],
                bdong_code=region_info["bdong_code"],
                plat_gb_cd=parsed.get("plat_gb_cd", "0"),
                bun=parsed.get("bun", ""),
                ji=parsed.get("ji", ""),
                num_of_rows=str(limit)
            )

            return {
                "status": "success" if result["success"] else "error",
                "address": address,
                "parsed_address": parsed,
                "region_info": {
                    "sigungu_name": region_info["sigungu_name"],
                    "bdong_name": region_info["bdong_name"],
                    "sigungu_code": region_info["sigungu_code"],
                    "bdong_code": region_info["bdong_code"]
                },
                "count": len(result.get("data", [])),
                "results": result.get("data", []),
                "page_info": result.get("page_info", {}),
                "info_type": info_type,
                "error": result.get("error") if not result["success"] else None
            }

        except Exception as e:
            logger.error(f"Address search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "address": address,
                "data": []
            }

    # =========================================================================
    # 내부 헬퍼 메서드
    # =========================================================================

    def _get_building_info(
        self,
        info_type: str,
        sigungu_code: str,
        bdong_code: str,
        plat_gb_cd: str,
        bun: str,
        ji: str,
        num_of_rows: str
    ) -> Dict[str, Any]:
        """
        건축물 정보 조회 (내부 메서드)

        Args:
            info_type: 조회 유형 (basic, summary, floor, dong, ho)
            sigungu_code: 시군구코드
            bdong_code: 법정동코드
            plat_gb_cd: 대지구분코드
            bun: 번지 (본번)
            ji: 번지 (부번)
            num_of_rows: 결과 개수

        Returns:
            API 응답
        """
        # 기본 정보 조회 (표제부)
        if info_type == "basic":
            return self.api.get_building_info(
                sigungu_cd=sigungu_code,
                bjdong_cd=bdong_code,
                plat_gb_cd=plat_gb_cd,
                bun=bun,
                ji=ji,
                num_of_rows=num_of_rows
            )

        # 다른 타입은 API 클래스 확장 필요
        # 현재는 basic만 지원
        else:
            return {
                "success": False,
                "error": f"Info type '{info_type}' not implemented yet. Only 'basic' is supported.",
                "data": []
            }

    def _parse_address(self, address: str) -> Dict[str, Any]:
        """
        주소 문자열 파싱

        Args:
            address: 주소 문자열 (예: "서울시 강남구 역삼동 123-45")

        Returns:
            파싱 결과 딕셔너리
        """
        try:
            # 공백 기준으로 분리
            parts = address.replace(",", " ").split()

            if len(parts) < 2:
                return {
                    "success": False,
                    "error": "주소 형식이 올바르지 않습니다. 최소한 시군구와 읍면동이 필요합니다."
                }

            # 시도 제거 (서울시, 경기도 등)
            sido_keywords = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
            filtered_parts = []

            for part in parts:
                # 시도 키워드 제거 (예: "서울시", "경기도")
                is_sido = False
                for sido in sido_keywords:
                    if part.startswith(sido) and (part.endswith("시") or part.endswith("도") or part == sido):
                        is_sido = True
                        break
                if not is_sido:
                    filtered_parts.append(part)

            if len(filtered_parts) < 2:
                return {
                    "success": False,
                    "error": "시군구와 읍면동을 찾을 수 없습니다."
                }

            # 시군구 추출 (첫 번째)
            sigungu = filtered_parts[0]

            # 읍면동 추출 (두 번째)
            bdong = filtered_parts[1]

            # 번지 추출 (세 번째 이후)
            bun = ""
            ji = ""

            if len(filtered_parts) >= 3:
                # 번지 파싱 (123-45 형식)
                bunji_str = filtered_parts[2]

                # "번지", "번", "-" 등 제거
                bunji_str = bunji_str.replace("번지", "").replace("번", "").strip()

                # 123-45 형식 파싱
                if "-" in bunji_str:
                    bunji_parts = bunji_str.split("-")
                    bun = bunji_parts[0].strip()
                    if len(bunji_parts) > 1:
                        ji = bunji_parts[1].strip()
                else:
                    bun = bunji_str.strip()

            # 대지구분코드 판단 (산인지 확인)
            plat_gb_cd = "0"  # 기본값: 대지
            if "산" in address:
                plat_gb_cd = "1"

            return {
                "success": True,
                "sigungu": sigungu,
                "bdong": bdong,
                "bun": bun,
                "ji": ji,
                "plat_gb_cd": plat_gb_cd,
                "original": address
            }

        except Exception as e:
            logger.error(f"Address parsing error: {e}")
            return {
                "success": False,
                "error": f"주소 파싱 중 오류 발생: {str(e)}"
            }

    def _format_building_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        건축물 데이터 포맷팅 (내부 메서드)

        Args:
            raw_data: API 원본 데이터

        Returns:
            포맷된 데이터
        """
        # 주요 필드 추출 및 한글화
        formatted = {
            "building_name": raw_data.get("bldNm", ""),  # 건물명
            "address": raw_data.get("platPlc", ""),  # 대지위치
            "main_use": raw_data.get("mainPurpsCdNm", ""),  # 주용도명
            "etc_use": raw_data.get("etcPurps", ""),  # 기타용도
            "structure": raw_data.get("strctCdNm", ""),  # 구조코드명
            "total_area": raw_data.get("totArea", ""),  # 연면적
            "floor_count_ground": raw_data.get("grndFlrCnt", ""),  # 지상층수
            "floor_count_underground": raw_data.get("ugrndFlrCnt", ""),  # 지하층수
            "approval_date": raw_data.get("useAprDay", ""),  # 사용승인일
            "permit_date": raw_data.get("pmsDay", ""),  # 허가일
            "raw": raw_data  # 원본 데이터 보존
        }

        return formatted


# =========================================================================
# 편의 함수
# =========================================================================

def create_building_registry_tool(service_key: Optional[str] = None) -> BuildingRegistryTool:
    """
    BuildingRegistryTool 인스턴스 생성 헬퍼 함수

    Args:
        service_key: 공공데이터 포털 Service Key (None이면 환경변수에서)

    Returns:
        BuildingRegistryTool 인스턴스
    """
    return BuildingRegistryTool(service_key=service_key)
