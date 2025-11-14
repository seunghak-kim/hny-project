"""
Market Data Tool - 부동산 시세 정보 제공
PostgreSQL 기반 실시간 데이터
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class MarketDataTool:
    """부동산 시세 데이터 Tool (PostgreSQL 연동)"""

    def __init__(self):
        # Lazy import로 순환 참조 방지
        from app.db.postgre_db import SessionLocal
        from app.models.real_estate import (
            RealEstate,
            Transaction,
            Region,
            PropertyType,
            TransactionType
        )

        self.SessionLocal = SessionLocal
        self.RealEstate = RealEstate
        self.Transaction = Transaction
        self.Region = Region
        self.PropertyType = PropertyType
        self.TransactionType = TransactionType

        logger.info("MarketDataTool initialized with PostgreSQL connection")

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        부동산 시세 검색 (PostgreSQL)

        Args:
            query: 사용자 쿼리
            params: {
                "region": "강남구",
                "property_type": "apartment" | "officetel" | "villa" | "oneroom" | "house",
                "transaction_type": "sale" | "jeonse" | "rent"
            }

        Returns:
            {
                "status": "success" | "error",
                "data": [...],
                "result_count": int,
                "metadata": {...}
            }
        """
        params = params or {}

        # 파라미터 추출
        region = params.get('region') or self._extract_region(query)
        property_type = params.get('property_type')
        transaction_type = params.get('transaction_type')

        logger.info(f"Market data search - region: {region}, type: {property_type}")

        db = self.SessionLocal()
        try:
            # DB 쿼리 실행
            results = self._query_market_data(
                db,
                region,
                property_type,
                transaction_type
            )

            return {
                "status": "success",
                "data": results,
                "result_count": len(results),
                "metadata": {
                    "region": region,
                    "property_type": property_type,
                    "transaction_type": transaction_type,
                    "data_source": "PostgreSQL"
                }
            }

        except Exception as e:
            logger.error(f"Market data search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "data": [],
                "result_count": 0
            }

        finally:
            db.close()

    def _query_market_data(
        self,
        db: Session,
        region: Optional[str],
        property_type: Optional[str],
        transaction_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        PostgreSQL에서 시세 데이터 조회 및 집계

        Returns:
            [
                {
                    "region": "강남구 역삼동",
                    "property_type": "apartment",
                    "avg_sale_price": 50000,  # 만원
                    "min_sale_price": 30000,
                    "max_sale_price": 100000,
                    "avg_deposit": 25000,
                    "min_deposit": 10000,
                    "max_deposit": 50000,
                    "avg_monthly_rent": 150,
                    "transaction_count": 100,
                    "unit": "만원"
                },
                ...
            ]
        """
        # 기본 쿼리: 지역별, 매물타입별 시세 집계
        # NULLIF(column, 0)을 사용하여 0 값을 NULL로 처리 → AVG 계산 시 자동 제외
        query = db.query(
            self.Region.name.label('region'),
            self.RealEstate.property_type.label('property_type'),
            func.avg(func.nullif(self.Transaction.min_sale_price, 0)).label('avg_sale_price'),
            func.min(func.nullif(self.Transaction.min_sale_price, 0)).label('min_sale_price'),
            func.max(func.nullif(self.Transaction.max_sale_price, 0)).label('max_sale_price'),
            func.avg(func.nullif(self.Transaction.min_deposit, 0)).label('avg_deposit'),
            func.min(func.nullif(self.Transaction.min_deposit, 0)).label('min_deposit'),
            func.max(func.nullif(self.Transaction.max_deposit, 0)).label('max_deposit'),
            func.avg(func.nullif(self.Transaction.min_monthly_rent, 0)).label('avg_monthly_rent'),
            func.count(self.Transaction.id).label('transaction_count')
        ).join(
            self.RealEstate,
            self.Transaction.real_estate_id == self.RealEstate.id
        ).join(
            self.Region,
            self.RealEstate.region_id == self.Region.id
        )

        # 필터 적용
        if region:
            query = query.filter(self.Region.name.contains(region))

        if property_type:
            # property_type이 문자열이면 Enum으로 변환
            if isinstance(property_type, str):
                try:
                    property_type_enum = self.PropertyType[property_type.upper()]
                    query = query.filter(self.RealEstate.property_type == property_type_enum)
                except KeyError:
                    logger.warning(f"Invalid property_type: {property_type}")

        if transaction_type:
            # transaction_type이 문자열이면 Enum으로 변환
            if isinstance(transaction_type, str):
                try:
                    transaction_type_enum = self.TransactionType[transaction_type.upper()]
                    query = query.filter(self.Transaction.transaction_type == transaction_type_enum)
                except KeyError:
                    logger.warning(f"Invalid transaction_type: {transaction_type}")

        # GROUP BY
        query = query.group_by(self.Region.name, self.RealEstate.property_type)

        # 거래 건수가 0보다 큰 것만 (데이터가 있는 것만)
        query = query.having(func.count(self.Transaction.id) > 0)

        # 결과 파싱
        results = []
        for row in query.all():
            # None을 0으로 변환 (NULLIF로 인해 값이 없으면 None 반환)
            result_item = {
                "region": row.region,
                "property_type": row.property_type.value,
                "avg_sale_price": int(row.avg_sale_price) if row.avg_sale_price is not None else None,
                "min_sale_price": int(row.min_sale_price) if row.min_sale_price is not None else None,
                "max_sale_price": int(row.max_sale_price) if row.max_sale_price is not None else None,
                "avg_deposit": int(row.avg_deposit) if row.avg_deposit is not None else None,
                "min_deposit": int(row.min_deposit) if row.min_deposit is not None else None,
                "max_deposit": int(row.max_deposit) if row.max_deposit is not None else None,
                "avg_monthly_rent": int(row.avg_monthly_rent) if row.avg_monthly_rent is not None else None,
                "transaction_count": row.transaction_count,
                "unit": "만원"
            }
            results.append(result_item)

        logger.info(f"Query returned {len(results)} market data records")
        return results

    def _extract_region(self, query: str) -> Optional[str]:
        """쿼리에서 지역명 추출"""
        regions = [
            "강남구", "서초구", "송파구", "강동구",
            "마포구", "용산구", "성동구", "광진구",
            "중구", "종로구", "노원구", "도봉구",
            "강북구", "성북구", "동대문구", "중랑구",
            "은평구", "서대문구", "강서구", "양천구",
            "구로구", "영등포구", "동작구", "관악구",
            "금천구"
        ]
        for region in regions:
            if region in query:
                return region
        return None
