"""
SQL Template Engine - 사전 정의된 SQL 패턴
안전하고 빠른 쿼리 생성
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SQLTemplate:
    """SQL 템플릿 정의"""
    name: str
    description: str
    sql: str
    required_params: List[str]
    optional_params: List[str]
    example_query: str


class SQLTemplateEngine:
    """
    SQL 템플릿 엔진
    - 사전 정의된 SQL 패턴을 사용하여 안전하고 빠른 쿼리 생성
    """

    def __init__(self):
        self.templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, SQLTemplate]:
        """템플릿 초기화"""
        return {
            "region_property_search": SQLTemplate(
                name="region_property_search",
                description="지역 + 매물 종류 기반 검색",
                sql="""
                    SELECT DISTINCT
                        re.id, re.name, re.address, re.property_type,
                        r.name as region_name,
                        re.latitude, re.longitude,
                        re.min_exclusive_area, re.max_exclusive_area,
                        re.completion_date,
                        t.min_sale_price, t.max_sale_price,
                        t.min_deposit, t.max_deposit,
                        re.total_households, re.total_buildings
                    FROM real_estates re
                    JOIN regions r ON re.region_id = r.id
                    LEFT JOIN transactions t ON t.real_estate_id = re.id
                    WHERE 1=1
                        {region_filter}
                        {property_type_filter}
                        {price_filter}
                        {area_filter}
                    ORDER BY re.id DESC
                    LIMIT :limit OFFSET :offset
                """,
                required_params=["limit", "offset"],
                optional_params=["region", "property_type", "min_price", "max_price", "min_area", "max_area"],
                example_query="강남구 아파트 5억 이하"
            ),

            "property_name_exact_search": SQLTemplate(
                name="property_name_exact_search",
                description="부동산 이름으로 정확 검색 (띄어쓰기 무시)",
                sql="""
                    SELECT
                        re.id, re.code, re.name, re.property_type,
                        re.address, re.latitude, re.longitude,
                        r.name as region_name,
                        re.total_households, re.completion_date,
                        re.min_exclusive_area, re.max_exclusive_area
                    FROM real_estates re
                    JOIN regions r ON re.region_id = r.id
                    WHERE REPLACE(re.name, ' ', '') = REPLACE(:property_name, ' ', '')
                    LIMIT 1
                """,
                required_params=["property_name"],
                optional_params=[],
                example_query="래미안대치팰리스"
            ),

            "market_average_price": SQLTemplate(
                name="market_average_price",
                description="지역별 평균 시세 조회",
                sql="""
                    SELECT
                        r.name as region,
                        re.property_type,
                        t.transaction_type,
                        AVG(NULLIF(t.min_sale_price, 0)) as avg_sale_price,
                        MIN(NULLIF(t.min_sale_price, 0)) as min_sale_price,
                        MAX(t.max_sale_price) as max_sale_price,
                        AVG(NULLIF(t.min_deposit, 0)) as avg_deposit,
                        COUNT(t.id) as transaction_count
                    FROM transactions t
                    JOIN real_estates re ON t.real_estate_id = re.id
                    JOIN regions r ON re.region_id = r.id
                    WHERE 1=1
                        {region_filter}
                        {property_type_filter}
                        {transaction_type_filter}
                        AND t.transaction_date >= NOW() - INTERVAL '1 year'
                    GROUP BY r.name, re.property_type, t.transaction_type
                    HAVING COUNT(t.id) > 0
                    ORDER BY r.name, re.property_type
                """,
                required_params=[],
                optional_params=["region", "property_type", "transaction_type"],
                example_query="서초구 아파트 평균 매매가"
            ),

            "price_range_filter": SQLTemplate(
                name="price_range_filter",
                description="가격 범위로 매물 검색",
                sql="""
                    SELECT DISTINCT
                        re.id, re.name, re.address,
                        r.name as region_name,
                        t.min_sale_price, t.max_sale_price,
                        t.min_deposit, t.max_deposit,
                        t.transaction_type
                    FROM real_estates re
                    JOIN regions r ON re.region_id = r.id
                    JOIN transactions t ON t.real_estate_id = re.id
                    WHERE 1=1
                        {region_filter}
                        {property_type_filter}
                        AND t.min_sale_price BETWEEN :min_price AND :max_price
                    ORDER BY t.min_sale_price ASC
                    LIMIT :limit
                """,
                required_params=["min_price", "max_price", "limit"],
                optional_params=["region", "property_type"],
                example_query="강남구 3억~5억 아파트"
            ),

            "area_range_filter": SQLTemplate(
                name="area_range_filter",
                description="면적 범위로 매물 검색",
                sql="""
                    SELECT
                        re.id, re.name, re.address,
                        r.name as region_name,
                        re.min_exclusive_area, re.max_exclusive_area,
                        re.representative_area,
                        t.min_sale_price, t.max_sale_price
                    FROM real_estates re
                    JOIN regions r ON re.region_id = r.id
                    LEFT JOIN transactions t ON t.real_estate_id = re.id
                    WHERE re.min_exclusive_area >= :min_area
                      AND re.max_exclusive_area <= :max_area
                      {region_filter}
                      {property_type_filter}
                    LIMIT :limit
                """,
                required_params=["min_area", "max_area", "limit"],
                optional_params=["region", "property_type"],
                example_query="60평~100평 아파트"
            ),
        }

    def render_template(self, template_name: str, params: Dict[str, Any]) -> str:
        """
        템플릿을 파라미터로 렌더링

        Args:
            template_name: 템플릿 이름
            params: 파라미터 딕셔너리

        Returns:
            렌더링된 SQL 문자열
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # 필수 파라미터 검증
        missing = [p for p in template.required_params if p not in params]
        if missing:
            raise ValueError(f"Missing required params: {missing}")

        sql = template.sql

        # 조건부 필터 렌더링
        filters = self._build_filters(params)

        # 플레이스홀더 치환
        sql = sql.format(
            region_filter=filters.get("region", ""),
            property_type_filter=filters.get("property_type", ""),
            transaction_type_filter=filters.get("transaction_type", ""),
            price_filter=filters.get("price", ""),
            area_filter=filters.get("area", "")
        )

        # 공백 정리
        sql = " ".join(sql.split())

        logger.info(f"Rendered template '{template_name}': {sql[:200]}...")
        return sql

    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, str]:
        """조건부 필터 SQL 생성"""
        filters = {}

        # 지역 필터
        if params.get("region"):
            filters["region"] = "AND r.name LIKE :region"

        # 매물 종류 필터
        if params.get("property_type"):
            filters["property_type"] = "AND re.property_type = :property_type"

        # 거래 종류 필터
        if params.get("transaction_type"):
            filters["transaction_type"] = "AND t.transaction_type = :transaction_type"

        # 가격 필터
        if params.get("min_price") or params.get("max_price"):
            price_conditions = []
            if params.get("min_price"):
                price_conditions.append("t.min_sale_price >= :min_price")
            if params.get("max_price"):
                price_conditions.append("t.max_sale_price <= :max_price")
            filters["price"] = "AND " + " AND ".join(price_conditions)

        # 면적 필터
        if params.get("min_area") or params.get("max_area"):
            area_conditions = []
            if params.get("min_area"):
                area_conditions.append("re.min_exclusive_area >= :min_area")
            if params.get("max_area"):
                area_conditions.append("re.max_exclusive_area <= :max_area")
            filters["area"] = "AND " + " AND ".join(area_conditions)

        return filters

    def match_template(self, query: str, params: Dict[str, Any]) -> Optional[str]:
        """
        쿼리와 파라미터에 가장 적합한 템플릿 찾기

        Returns:
            템플릿 이름 또는 None
        """
        # 부동산 이름이 있으면 정확 검색 템플릿
        if params.get("property_name"):
            return "property_name_exact_search"

        # "평균", "시세" 키워드 → 시장 데이터
        if any(kw in query for kw in ["평균", "시세", "얼마"]):
            return "market_average_price"

        # 가격 범위만 있으면 가격 필터
        if params.get("min_price") and params.get("max_price") and not params.get("min_area"):
            return "price_range_filter"

        # 면적 범위만 있으면 면적 필터
        if params.get("min_area") and params.get("max_area"):
            return "area_range_filter"

        # 기본: 지역 + 매물 검색
        if params.get("region") or params.get("property_type"):
            return "region_property_search"

        # 매칭 실패
        return None

    def get_template_confidence(self, template_name: str, params: Dict[str, Any]) -> float:
        """
        템플릿 적합도 점수 계산

        Returns:
            0.0 ~ 1.0 사이의 신뢰도
        """
        template = self.templates.get(template_name)
        if not template:
            return 0.0

        score = 0.0

        # 필수 파라미터가 모두 있으면 +0.5
        if all(p in params for p in template.required_params):
            score += 0.5

        # 선택적 파라미터가 있으면 각각 +0.1 (최대 0.5)
        optional_present = sum(1 for p in template.optional_params if params.get(p))
        score += min(optional_present * 0.1, 0.5)

        return min(score, 1.0)
