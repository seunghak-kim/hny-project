"""
Real Estate Search Tool - 부동산 매물 검색
PostgreSQL 기반 매물 정보 조회
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


class RealEstateSearchTool:
    """부동산 매물 검색 Tool (PostgreSQL 연동)"""

    def __init__(self):
        # Lazy import로 순환 참조 방지
        self._ensure_db_imports()
        logger.info("RealEstateSearchTool initialized with PostgreSQL connection")

    def _ensure_db_imports(self):
        """필요할 때만 import (Lazy Loading)"""
        if not hasattr(self, 'SessionLocal'):
            from app.db.postgre_db import SessionLocal
            from app.models.real_estate import (
                RealEstate,
                Region,
                Transaction,
                NearbyFacility,
                RealEstateAgent,
                PropertyType,
                TransactionType
            )
            from app.models.trust import TrustScore

            self.SessionLocal = SessionLocal
            self.RealEstate = RealEstate
            self.Region = Region
            self.Transaction = Transaction
            self.NearbyFacility = NearbyFacility
            self.RealEstateAgent = RealEstateAgent
            self.PropertyType = PropertyType
            self.TransactionType = TransactionType
            self.TrustScore = TrustScore

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        부동산 매물 검색 (PostgreSQL)

        Args:
            query: 사용자 쿼리
            params: {
                "region": "강남구",
                "property_type": "apartment" | "officetel" | "villa" | "oneroom" | "house",
                "min_area": 60.0,  # ㎡
                "max_area": 120.0,
                "min_price": 10000,  # 만원
                "max_price": 50000,
                "completion_year": "2020",
                "limit": 10,
                "offset": 0,
                "include_nearby": True,  # 주변 시설 정보 포함 여부
                "include_transactions": True,  # 최근 거래 내역 포함 여부
                "include_agent": False  # 중개사 정보 포함 여부
            }

        Returns:
            {
                "status": "success" | "error",
                "data": [...],
                "result_count": int,
                "metadata": {
                    "region": str,
                    "property_type": str,
                    "filters": {...},
                    "data_source": "PostgreSQL"
                }
            }
        """
        params = params or {}

        # 파라미터 추출
        region = params.get('region') or self._extract_region(query)
        property_type = params.get('property_type')
        min_area = params.get('min_area')
        max_area = params.get('max_area')
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        completion_year = params.get('completion_year')
        limit = params.get('limit', 10)
        offset = params.get('offset', 0)
        include_nearby = params.get('include_nearby', False)
        include_transactions = params.get('include_transactions', True)
        include_agent = params.get('include_agent', False)

        logger.info(
            f"Real estate search - region: {region}, type: {property_type}, "
            f"price: {min_price}-{max_price}, area: {min_area}-{max_area}, "
            f"limit: {limit}, offset: {offset}"
        )

        db = self.SessionLocal()
        try:
            # DB 쿼리 실행
            results = self._query_real_estates(
                db, region, property_type, min_area, max_area,
                min_price, max_price, completion_year,
                limit, offset, include_nearby, include_transactions, include_agent
            )

            return {
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
                }
            }

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

    def _query_real_estates(
        self,
        db: Session,
        region: Optional[str],
        property_type: Optional[str],
        min_area: Optional[float],
        max_area: Optional[float],
        min_price: Optional[int],
        max_price: Optional[int],
        completion_year: Optional[str],
        limit: int,
        offset: int,
        include_nearby: bool,
        include_transactions: bool,
        include_agent: bool
    ) -> List[Dict[str, Any]]:
        """
        PostgreSQL에서 부동산 매물 조회

        ⚠️ Phase 1 경험 반영:
        - 가격 필터 시 min_sale_price 사용 (sale_price 아님!)
        - Transaction 조인 시 거래 타입 고려
        - Enum 변환 시 예외 처리
        """
        # 기본 쿼리
        query = db.query(self.RealEstate).join(self.Region)

        # Eager loading으로 N+1 문제 방지
        if include_transactions:
            query = query.options(
                joinedload(self.RealEstate.region),
                joinedload(self.RealEstate.transactions),
                joinedload(self.RealEstate.trust_scores)  # trust_score 항상 포함
            )
        else:
            query = query.options(
                joinedload(self.RealEstate.region),
                joinedload(self.RealEstate.trust_scores)  # trust_score 항상 포함
            )

        # 중개사 정보 조건부 로딩
        if include_agent:
            query = query.options(joinedload(self.RealEstate.agent))

        # ⚠️ nearby_facility는 RealEstate에 relationship이 없으므로 주석 처리
        # 향후 모델에 relationship 추가 후 활성화
        # if include_nearby:
        #     query = query.options(joinedload(self.RealEstate.nearby_facility))

        # 필터 적용
        if region:
            query = query.filter(self.Region.name.contains(region))

        if property_type:
            try:
                if isinstance(property_type, str):
                    property_type_enum = self.PropertyType[property_type.upper()]
                    query = query.filter(self.RealEstate.property_type == property_type_enum)
            except KeyError:
                logger.warning(f"Invalid property_type: {property_type}")
                # 잘못된 타입이면 필터 적용 안 함

        if min_area:
            query = query.filter(self.RealEstate.min_exclusive_area >= min_area)

        if max_area:
            query = query.filter(self.RealEstate.max_exclusive_area <= max_area)

        if completion_year:
            query = query.filter(
                self.RealEstate.completion_date.like(f'{completion_year}%')
            )

        # ⚠️ 가격 필터 (Transaction 조인 필요)
        # Phase 1 경험: min_sale_price 사용 (sale_price 아님!)
        if min_price or max_price:
            query = query.join(self.Transaction)

            if min_price:
                # min_sale_price 사용 (sale_price 아님!)
                query = query.filter(self.Transaction.min_sale_price >= min_price)

            if max_price:
                # max_sale_price 사용
                query = query.filter(self.Transaction.max_sale_price <= max_price)

            # 중복 제거 (하나의 부동산이 여러 거래를 가질 수 있음)
            query = query.distinct()

        # Pagination
        query = query.limit(limit).offset(offset)

        # 결과 파싱
        results = []
        for estate in query.all():
            estate_data = {
                "id": estate.id,
                "code": estate.code,
                "name": estate.name,
                "property_type": estate.property_type.value if estate.property_type else None,
                "region": estate.region.name if estate.region else None,
                "address": estate.address,
                "latitude": float(estate.latitude) if estate.latitude else None,
                "longitude": float(estate.longitude) if estate.longitude else None,
                "total_households": estate.total_households,
                "total_buildings": estate.total_buildings,
                "completion_date": estate.completion_date,
                "min_exclusive_area": float(estate.min_exclusive_area) if estate.min_exclusive_area else None,
                "max_exclusive_area": float(estate.max_exclusive_area) if estate.max_exclusive_area else None,
                "representative_area": float(estate.representative_area) if estate.representative_area else None,
                "building_description": estate.building_description,
                "tags": estate.tag_list,
                # 신뢰도 점수 (Q3: 항상 포함, 없으면 None)
                "trust_score": float(estate.trust_scores[0].score) if estate.trust_scores else None
            }

            # 최근 거래 내역 (최대 5개)
            if include_transactions and hasattr(estate, 'transactions') and estate.transactions:
                estate_data["recent_transactions"] = []

                # 거래 날짜로 정렬
                sorted_transactions = sorted(
                    estate.transactions,
                    key=lambda x: x.transaction_date if x.transaction_date else "",
                    reverse=True
                )[:5]

                for t in sorted_transactions:
                    transaction_data = {
                        "transaction_type": t.transaction_type.value if t.transaction_type else None,
                        "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                    }

                    # ⚠️ Phase 1 경험: min_sale_price, min_deposit, min_monthly_rent 사용
                    # 단일 필드(sale_price, deposit)는 대부분 0이므로 범위 필드 사용
                    if t.min_sale_price and t.min_sale_price > 0:
                        transaction_data["sale_price_range"] = {
                            "min": t.min_sale_price,
                            "max": t.max_sale_price or t.min_sale_price,
                            "unit": "만원"
                        }

                    if t.min_deposit and t.min_deposit > 0:
                        transaction_data["deposit_range"] = {
                            "min": t.min_deposit,
                            "max": t.max_deposit or t.min_deposit,
                            "unit": "만원"
                        }

                    if t.min_monthly_rent and t.min_monthly_rent > 0:
                        transaction_data["monthly_rent_range"] = {
                            "min": t.min_monthly_rent,
                            "max": t.max_monthly_rent or t.min_monthly_rent,
                            "unit": "만원"
                        }

                    estate_data["recent_transactions"].append(transaction_data)

            # ⚠️ 주변 시설 정보 (현재 relationship 없음 - 별도 쿼리로 조회 필요)
            if include_nearby:
                # NearbyFacility를 별도 쿼리로 조회
                nearby = db.query(self.NearbyFacility).filter(
                    self.NearbyFacility.real_estate_id == estate.id
                ).first()

                if nearby:
                    estate_data["nearby_facilities"] = {
                        "subway": {
                            "line": nearby.subway_line,
                            "station": getattr(nearby, 'subway_station', None),
                            "distance": nearby.subway_distance,
                            "walking_time": nearby.subway_walking_time
                        } if nearby.subway_line else None,
                        "schools": {
                            "elementary": nearby.elementary_schools.split(',') if nearby.elementary_schools else [],
                            "middle": nearby.middle_schools.split(',') if nearby.middle_schools else [],
                            "high": nearby.high_schools.split(',') if nearby.high_schools else []
                        }
                    }

            # 중개사 정보 (Q5: 데이터 있으면 포함)
            if include_agent and hasattr(estate, 'agent') and estate.agent:
                estate_data["agent_info"] = {
                    "agent_name": estate.agent.agent_name,
                    "company_name": estate.agent.company_name,
                    "is_direct_trade": estate.agent.is_direct_trade
                }

            results.append(estate_data)

        return results

    def _extract_region(self, query: str) -> Optional[str]:
        """쿼리에서 지역명 추출 (기존 로직 유지)"""
        regions = [
            "강남구", "서초구", "송파구", "강동구",
            "마포구", "용산구", "성동구", "광진구",
            "중구", "종로구", "노원구", "도봉구",
            "강북구", "성북구", "동대문구", "중랑구",
            "영등포구", "동작구", "관악구", "서대문구",
            "은평구", "양천구", "구로구", "금천구", "강서구"
        ]

        for region in regions:
            if region in query:
                return region

        return None
