"""
부동산 데이터 API
지도 viewport 기반 부동산 조회 엔드포인트
"""

import asyncio
from typing import List, Optional, Dict, Any, Union, Tuple
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy import and_, or_, func, case, literal_column
from pydantic import BaseModel, Field, ConfigDict

from app.db.postgre_db import get_db
from app.models.building import Building
from app.models.region import Region
from app.models.infrastructure import Infrastructure
from app.models.transaction.transaction import Transaction
from app.models.transaction.sale_transaction import SaleTransaction
from app.models.transaction.rent_transaction import RentTransaction
from app.models.enums import PropertyType, TransactionType

router = APIRouter(prefix="/api/real-estate", tags=["real-estate"])


# ============================================================================
# Response Models
# ============================================================================

class ClusterResponse(BaseModel):
    """클러스터 응답 모델"""
    type: str = Field("cluster", description="데이터 유형 (항상 'cluster')")
    count: int = Field(..., description="클러스터 내 부동산 개수")
    latitude: float = Field(..., description="클러스터 중심 위도")
    longitude: float = Field(..., description="클러스터 중심 경도")


class DongResponse(BaseModel):
    """동 단위 집계 응답 모델"""
    type: str = Field("dong", description="데이터 유형 (항상 'dong')")
    gu: str = Field(..., description="구 이름")
    dong: str = Field(..., description="동 이름")
    count: int = Field(..., description="매물 개수")
    property_type: str = Field("동 최저가", description="프론트엔드 클러스터링용 타입")
    latitude: float = Field(..., description="동 중심 위도")
    longitude: float = Field(..., description="동 중심 경도")

    # 최저 가격 (억원 단위) - 필드명은 avg_*이지만 최저가를 담음
    avg_sale_price_eok: Optional[str] = None
    avg_jeonse_price_eok: Optional[str] = None
    avg_rent_price_eok: Optional[str] = None

    # 거래 건수
    total_transactions: int = 0


class GuResponse(BaseModel):
    """구 단위 집계 응답 모델"""
    type: str = Field("gu", description="데이터 유형 (항상 'gu')")
    gu: str = Field(..., description="구 이름")
    count: int = Field(..., description="매물 개수")
    property_type: str = Field("구 최저가", description="프론트엔드 클러스터링용 타입")
    latitude: float = Field(..., description="구 중심 위도")
    longitude: float = Field(..., description="구 중심 경도")

    # 최저 가격 (억원 단위) - 필드명은 avg_*이지만 최저가를 담음
    avg_sale_price_eok: Optional[str] = None
    avg_jeonse_price_eok: Optional[str] = None
    avg_rent_price_eok: Optional[str] = None

    # 거래 건수
    total_transactions: int = 0


class PropertyResponse(BaseModel):
    """부동산 응답 모델"""
    id: int
    code: str = ""
    name: str
    property_type: str
    latitude: float
    longitude: float

    # 기본 정보
    gu: str = ""
    dong: str = ""
    total_households: Optional[int] = None
    total_buildings: Optional[int] = None
    completion_date: Optional[str] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    address: Optional[str] = None

    # 거래 건수
    deal_count: int = 0
    lease_count: int = 0
    rent_count: int = 0
    total_article_count: int = 0

    # 가격 정보 (만원 단위 - raw)
    sale_min_price: Optional[int] = None
    sale_max_price: Optional[int] = None
    jeonse_min_price: Optional[int] = None
    jeonse_max_price: Optional[int] = None
    rent_min_price: Optional[int] = None
    rent_max_price: Optional[int] = None

    # 가격 정보 (억원 단위 - 표시용)
    sale_min_price_eok: Optional[str] = None
    sale_max_price_eok: Optional[str] = None
    jeonse_min_price_eok: Optional[str] = None
    jeonse_max_price_eok: Optional[str] = None
    rent_min_price_eok: Optional[str] = None
    rent_max_price_eok: Optional[str] = None

    # 면적 요약
    area_summary: Optional[str] = None

    # 주변 시설 정보 (JSON 문자열)
    nearby_subway_stations: Optional[str] = None
    nearby_schools: Optional[str] = None
    nearby_marts: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def format_eok(value: Optional[int]) -> str:
    """만원을 억원으로 변환"""
    if not value or value == 0:
        return ""
    try:
        eok = value / 10000
        # 억 단위 추가
        if eok % 1 != 0:
            return f"{eok:.1f}억"
        else:
            return f"{int(eok)}억"
    except:
        return ""


def _build_subqueries(db: Session, bounds: Optional[Dict[str, float]] = None, building_ids: Optional[List[int]] = None):
    """
    매매/전세/월세 각각에 대한 서브쿼리를 생성합니다.
    bounds가 주어지면 해당 범위 내의 건물에 대한 거래만 집계하여 성능을 최적화합니다.
    building_ids가 주어지면 해당 ID 목록에 있는 건물의 거래만 집계합니다.
    """
    # 공통 필터링 로직
    def apply_bounds_filter(query):
        if building_ids:
            query = query.filter(Transaction.building_id.in_(building_ids))
        elif bounds:
            query = query.join(Building, Transaction.building_id == Building.id)\
                         .filter(
                             Building.latitude >= bounds["south"],
                             Building.latitude <= bounds["north"],
                             Building.longitude >= bounds["west"],
                             Building.longitude <= bounds["east"]
                         )
        return query

    # 1. 매매 서브쿼리
    sale_query = db.query(
        Transaction.building_id,
        func.min(SaleTransaction.deal_amount).label('min_sale_price'),
        func.max(SaleTransaction.deal_amount).label('max_sale_price'),
        func.count(SaleTransaction.id).label('sale_count')
    ).join(
        Transaction, SaleTransaction.transaction_id == Transaction.id
    ).filter(
        Transaction.transaction_type == TransactionType.SALE
    )
    sale_query = apply_bounds_filter(sale_query)
    sale_subquery = sale_query.group_by(Transaction.building_id).subquery()

    # 2. 전세 서브쿼리
    jeonse_query = db.query(
        Transaction.building_id,
        func.min(RentTransaction.deposit).label('min_jeonse_price'),
        func.max(RentTransaction.deposit).label('max_jeonse_price'),
        func.count(RentTransaction.id).label('jeonse_count')
    ).join(
        Transaction, RentTransaction.transaction_id == Transaction.id
    ).filter(
        Transaction.transaction_type == TransactionType.RENT,
        RentTransaction.monthly_rent == 0
    )
    jeonse_query = apply_bounds_filter(jeonse_query)
    jeonse_subquery = jeonse_query.group_by(Transaction.building_id).subquery()

    # 3. 월세 서브쿼리
    rent_query = db.query(
        Transaction.building_id,
        func.min(RentTransaction.monthly_rent).label('min_rent_price'),
        func.max(RentTransaction.monthly_rent).label('max_rent_price'),
        func.count(RentTransaction.id).label('rent_count')
    ).join(
        Transaction, RentTransaction.transaction_id == Transaction.id
    ).filter(
        Transaction.transaction_type == TransactionType.RENT,
        RentTransaction.monthly_rent > 0
    )
    rent_query = apply_bounds_filter(rent_query)
    rent_subquery = rent_query.group_by(Transaction.building_id).subquery()

    return sale_subquery, jeonse_subquery, rent_subquery


def _apply_filters(
    query,
    Building,
    sale_subquery,
    jeonse_subquery,
    rent_subquery,
    bounds: Dict[str, float],
    property_types: Optional[List[str]],
    transaction_type: Optional[str],
    min_price: Optional[int],
    max_price: Optional[int]
):
    """공통 필터 적용"""
    # Viewport Filter
    query = query.filter(
        and_(
            Building.latitude.between(bounds['south'], bounds['north']),
            Building.longitude.between(bounds['west'], bounds['east']),
            Building.latitude.isnot(None),
            Building.longitude.isnot(None)
        )
    )

    # Property Type Filter
    if property_types:
        type_enums = []
        for pt in property_types:
            try:
                type_enums.append(PropertyType(pt.lower()))
            except ValueError:
                pass
        if type_enums:
            query = query.filter(Building.building_type.in_(type_enums))

    # Transaction Type Filter
    if transaction_type:
        if transaction_type.lower() == "sale":
            query = query.filter(sale_subquery.c.sale_count > 0)
        elif transaction_type.lower() == "jeonse":
            query = query.filter(jeonse_subquery.c.jeonse_count > 0)
        elif transaction_type.lower() == "rent":
            query = query.filter(rent_subquery.c.rent_count > 0)

    # Price Filter (만원 단위)
    if min_price is not None or max_price is not None:
        price_filters = []
        min_p = min_price * 10000 if min_price is not None else None
        max_p = max_price * 10000 if max_price is not None else None

        if min_p is not None:
            price_filters.append(or_(
                sale_subquery.c.min_sale_price >= min_p,
                jeonse_subquery.c.min_jeonse_price >= min_p
            ))
        if max_p is not None:
            price_filters.append(or_(
                sale_subquery.c.min_sale_price <= max_p,
                jeonse_subquery.c.min_jeonse_price <= max_p
            ))

        if price_filters:
            query = query.filter(and_(*price_filters))
            
    return query


async def _process_properties(
    db: Session,
    bounds: Dict[str, float],
    limit: int,
    property_types: Optional[List[str]],
    transaction_type: Optional[str],
    min_price: Optional[int],
    max_price: Optional[int]
) -> List[PropertyResponse]:
    """부동산 데이터를 조회하고 처리하는 공통 함수"""

    target_ids = None
    if min_price is None and max_price is None:
        # 최적화: 가격 필터가 없는 경우 (사이드바 검색 등)
        # 먼저 건물 ID 목록을 가져온 후, 해당 건물의 거래 내역만 조회 (Global Aggregation 방지)
        
        # 1. 건물 ID 조회
        id_query = db.query(Building.id)
        
        # Bounds Filter
        if bounds:
            id_query = id_query.filter(
                Building.latitude >= bounds['south'],
                Building.latitude <= bounds['north'],
                Building.longitude >= bounds['west'],
                Building.longitude <= bounds['east']
            )
            
        # Property Type Filter
        if property_types:
            type_enums = []
            for pt in property_types:
                try:
                    type_enums.append(PropertyType(pt.lower()))
                except ValueError:
                    pass
            if type_enums:
                id_query = id_query.filter(Building.building_type.in_(type_enums))
        
        # Limit 적용
        target_ids = [r[0] for r in id_query.limit(limit).all()]
        
        if not target_ids:
            return []
            
        # 2. 서브쿼리 생성 (ID 기반)
        sale_subquery, jeonse_subquery, rent_subquery = _build_subqueries(db, building_ids=target_ids)
    else:
        # 기존 로직: Bounds 기반 서브쿼리
        # 1. 서브쿼리 생성 (bounds 필터링 적용)
        sale_subquery, jeonse_subquery, rent_subquery = _build_subqueries(db, bounds=bounds)

    # 3. 메인 쿼리 (Building, Region, Infrastructure 조인)
    query = db.query(
        Building,
        Region,
        Infrastructure if limit <= 10000 else literal_column('NULL').label('infrastructure'),
        sale_subquery.c.min_sale_price, sale_subquery.c.max_sale_price, sale_subquery.c.sale_count,
        jeonse_subquery.c.min_jeonse_price, jeonse_subquery.c.max_jeonse_price, jeonse_subquery.c.jeonse_count,
        rent_subquery.c.min_rent_price, rent_subquery.c.max_rent_price, rent_subquery.c.rent_count
    ).join(
        Region, Building.region_id == Region.id
    )

    # limit이 작을 때만 Infrastructure 조인 (성능 최적화)
    if limit <= 10000:
        query = query.outerjoin(
            Infrastructure, Building.id == Infrastructure.building_id
        )

    query = query.outerjoin(
        sale_subquery, Building.id == sale_subquery.c.building_id
    ).outerjoin(
        jeonse_subquery, Building.id == jeonse_subquery.c.building_id
    ).outerjoin(
        rent_subquery, Building.id == rent_subquery.c.building_id
    )

    # 4. 필터 적용
    if target_ids is not None:
        # 최적화 경로: ID로 필터링
        query = query.filter(Building.id.in_(target_ids))
        # Bounds, property_types, limit은 이미 target_ids를 생성할 때 적용됨
    else:
        # 기존 경로: 공통 필터 적용
        query = _apply_filters(
            query, Building, sale_subquery, jeonse_subquery, rent_subquery,
            bounds, property_types, transaction_type, min_price, max_price
        )
        query = query.limit(limit)

    properties = query.all()

    # 4. 결과 포맷팅
    result = []
    for building, region, infra, min_s, max_s, s_cnt, min_j, max_j, j_cnt, min_r, max_r, r_cnt in properties:
        gu = region.gu_name if region else ""
        dong = building.legal_dong if building.legal_dong else ""

        property_name = building.name
        if not property_name or property_name.strip() in ['-', '']:
            property_name = f"{gu} {dong}" if gu and dong else property_name

        include_facilities = limit <= 10000
        
        area_summary = ""
        if building.min_area:
            min_pyeong = float(building.min_area) / 3.3058
            area_summary = f"{float(building.min_area):.0f}㎡({min_pyeong:.0f}평)"
            if building.max_area and building.max_area != building.min_area:
                max_pyeong = float(building.max_area) / 3.3058
                area_summary += f" ~ {float(building.max_area):.0f}㎡({max_pyeong:.0f}평)"

        type_map = {
            PropertyType.APARTMENT: "아파트",
            PropertyType.OFFICETEL: "오피스텔",
            PropertyType.VILLA: "빌라",
            PropertyType.HOUSE: "단독/다가구"
        }
        property_type_kor = type_map.get(building.building_type, building.building_type.value)

        prop_data = PropertyResponse(
            id=building.id,
            code=str(building.id),
            name=property_name,
            property_type=property_type_kor,
            latitude=float(building.latitude) if building.latitude is not None else 0.0,
            longitude=float(building.longitude) if building.longitude is not None else 0.0,
            gu=gu,
            dong=dong,
            completion_date=building.build_year,
            min_area=float(building.min_area) if building.min_area else None,
            max_area=float(building.max_area) if building.max_area else None,
            address=building.address,
            deal_count=s_cnt or 0,
            lease_count=j_cnt or 0,
            rent_count=r_cnt or 0,
            total_article_count=(s_cnt or 0) + (j_cnt or 0) + (r_cnt or 0),
            sale_min_price=min_s, sale_max_price=max_s,
            jeonse_min_price=min_j, jeonse_max_price=max_j,
            rent_min_price=min_r, rent_max_price=max_r,
            sale_min_price_eok=format_eok(min_s), sale_max_price_eok=format_eok(max_s),
            jeonse_min_price_eok=format_eok(min_j), jeonse_max_price_eok=format_eok(max_j),
            rent_min_price_eok=format_eok(min_r), rent_max_price_eok=format_eok(max_r),
            area_summary=area_summary,
            nearby_subway_stations=infra.nearby_subway_stations if infra and include_facilities else None,
            nearby_schools=infra.nearby_schools if infra and include_facilities else None,
            nearby_marts=infra.nearby_marts if infra and include_facilities else None
        )
        result.append(prop_data)
    return result


def _get_dong_aggregation(
    db: Session,
    bounds: Dict[str, float],
    property_types: Optional[List[str]],
    transaction_type: Optional[str],
    min_price: Optional[int],
    max_price: Optional[int]
) -> List[DongResponse]:
    """동 단위 DB 집계"""
    # 1. 서브쿼리 생성 (bounds 필터링 적용)
    sale_subquery, jeonse_subquery, rent_subquery = _build_subqueries(db, bounds)

    # 집계 쿼리
    query = db.query(
        Region.gu_name,
        Building.legal_dong,
        func.count(Building.id).label('count'),
        func.avg(Building.latitude).label('avg_lat'),
        func.avg(Building.longitude).label('avg_lng'),
        func.avg(sale_subquery.c.max_sale_price).label('avg_sale'),
        func.avg(jeonse_subquery.c.max_jeonse_price).label('avg_jeonse'),
        func.avg(rent_subquery.c.max_rent_price).label('avg_rent'),
        func.sum(func.coalesce(sale_subquery.c.sale_count, 0) + 
                 func.coalesce(jeonse_subquery.c.jeonse_count, 0) + 
                 func.coalesce(rent_subquery.c.rent_count, 0)).label('total_trans')
    ).join(
        Region, Building.region_id == Region.id
    ).outerjoin(
        sale_subquery, Building.id == sale_subquery.c.building_id
    ).outerjoin(
        jeonse_subquery, Building.id == jeonse_subquery.c.building_id
    ).outerjoin(
        rent_subquery, Building.id == rent_subquery.c.building_id
    )

    query = _apply_filters(
        query, Building, sale_subquery, jeonse_subquery, rent_subquery,
        bounds, property_types, transaction_type, min_price, max_price
    )

    # Group by
    results = query.group_by(Region.gu_name, Building.legal_dong).all()

    response = []
    for row in results:
        if not row.legal_dong:
            continue
            
        response.append(DongResponse(
            type="dong",
            gu=row.gu_name,
            dong=row.legal_dong,
            count=row.count,
            property_type="동 최저가",
            latitude=float(row.avg_lat) if row.avg_lat else 0.0,
            longitude=float(row.avg_lng) if row.avg_lng else 0.0,
            avg_sale_price_eok=format_eok(int(row.avg_sale)) if row.avg_sale else None,
            avg_jeonse_price_eok=format_eok(int(row.avg_jeonse)) if row.avg_jeonse else None,
            avg_rent_price_eok=format_eok(int(row.avg_rent)) if row.avg_rent else None,
            total_transactions=int(row.total_trans) if row.total_trans else 0
        ))
    return response


def _get_gu_aggregation(
    db: Session,
    bounds: Dict[str, float],
    property_types: Optional[List[str]],
    transaction_type: Optional[str],
    min_price: Optional[int],
    max_price: Optional[int]
) -> List[GuResponse]:
    """구 단위 DB 집계"""
    # 1. 서브쿼리 생성 (bounds 필터링 적용)
    sale_subquery, jeonse_subquery, rent_subquery = _build_subqueries(db, bounds)

    # 집계 쿼리
    query = db.query(
        Region.gu_name,
        func.count(Building.id).label('count'),
        func.avg(Building.latitude).label('avg_lat'),
        func.avg(Building.longitude).label('avg_lng'),
        func.avg(sale_subquery.c.max_sale_price).label('avg_sale'),
        func.avg(jeonse_subquery.c.max_jeonse_price).label('avg_jeonse'),
        func.avg(rent_subquery.c.max_rent_price).label('avg_rent'),
        func.sum(func.coalesce(sale_subquery.c.sale_count, 0) + 
                 func.coalesce(jeonse_subquery.c.jeonse_count, 0) + 
                 func.coalesce(rent_subquery.c.rent_count, 0)).label('total_trans')
    ).join(
        Region, Building.region_id == Region.id
    ).outerjoin(
        sale_subquery, Building.id == sale_subquery.c.building_id
    ).outerjoin(
        jeonse_subquery, Building.id == jeonse_subquery.c.building_id
    ).outerjoin(
        rent_subquery, Building.id == rent_subquery.c.building_id
    )

    query = _apply_filters(
        query, Building, sale_subquery, jeonse_subquery, rent_subquery,
        bounds, property_types, transaction_type, min_price, max_price
    )

    # Group by
    results = query.group_by(Region.gu_name).all()

    response = []
    for row in results:
        if not row.gu_name:
            continue
            
        response.append(GuResponse(
            type="gu",
            gu=row.gu_name,
            count=row.count,
            property_type="구 최저가",
            latitude=float(row.avg_lat) if row.avg_lat else 0.0,
            longitude=float(row.avg_lng) if row.avg_lng else 0.0,
            avg_sale_price_eok=format_eok(int(row.avg_sale)) if row.avg_sale else None,
            avg_jeonse_price_eok=format_eok(int(row.avg_jeonse)) if row.avg_jeonse else None,
            avg_rent_price_eok=format_eok(int(row.avg_rent)) if row.avg_rent else None,
            total_transactions=int(row.total_trans) if row.total_trans else 0
        ))
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/properties", response_model=List[Union[GuResponse, DongResponse, ClusterResponse, PropertyResponse]])
async def get_properties(
    # Viewport bounds
    south: float = Query(..., description="남쪽 위도 (viewport 하단)"),
    north: float = Query(..., description="북쪽 위도 (viewport 상단)"),
    west: float = Query(..., description="서쪽 경도 (viewport 좌측)"),
    east: float = Query(..., description="동쪽 경도 (viewport 우측)"),

    # Zoom level for optimization
    zoom: Optional[int] = Query(None, description="지도 줌 레벨 (1-14)"),

    # Filters
    property_types: Optional[str] = Query(None, description="부동산 유형 (쉼표로 구분: apartment,officetel,villa,house)"),
    transaction_type: Optional[str] = Query(None, description="거래 유형 (sale, jeonse, rent)"),
    min_price: Optional[int] = Query(None, description="최소 가격 (억원)"),
    max_price: Optional[int] = Query(None, description="최대 가격 (억원)"),

    # Pagination
    limit: int = Query(5000, le=20000, description="최대 결과 수"),
    offset: int = Query(0, description="결과 오프셋"),

    db: Session = Depends(get_db)
):
    """
    지도 viewport 기반 부동산 조회
    """

    # DB 조회 limit 설정
    db_limit = limit if limit > 10000 else min(limit, 5000)

    # Property Types 파싱
    pt_list = None
    if property_types:
        pt_list = [pt.strip().lower() for pt in property_types.split(',')]

    bounds = {"south": south, "north": north, "west": west, "east": east}

    # 줌 레벨에 따른 집계 전략
    if zoom and zoom >= 7:
        # 구 단위 DB 집계 (줌 레벨 7 이상, 즉 축소된 상태)
        return _get_gu_aggregation(
            db, bounds, pt_list, transaction_type, min_price, max_price
        )
    elif zoom and 5 <= zoom <= 6:
        # 동 단위 DB 집계
        return _get_dong_aggregation(
            db, bounds, pt_list, transaction_type, min_price, max_price
        )

    # 그 외의 줌 레벨에서는 개별 매물 데이터를 반환
    return await _process_properties(
        db, bounds, db_limit, pt_list, transaction_type, min_price, max_price
    )


@router.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    부동산 데이터 통계
    """
    # 1. 부동산 유형별 건수
    # Building 테이블에서 building_type별로 그룹화하여 카운트
    building_counts = db.query(
        Building.building_type, func.count(Building.id)
    ).group_by(Building.building_type).all()
    
    by_type = {
        "아파트": 0,
        "오피스텔": 0,
        "빌라": 0,
        "단독/다가구": 0
    }
    
    type_map = {
        PropertyType.APARTMENT: "아파트",
        PropertyType.OFFICETEL: "오피스텔",
        PropertyType.VILLA: "빌라",
        PropertyType.HOUSE: "단독/다가구"
    }
    
    total_properties = 0
    for b_type, count in building_counts:
        if b_type in type_map:
            by_type[type_map[b_type]] = count
            total_properties += count

    # 2. 거래 건수 (유형별 + 거래종류별)
    # Transaction 테이블과 Building 테이블을 조인하여 집계
    transaction_counts = db.query(
        Building.building_type,
        Transaction.transaction_type,
        func.count(Transaction.id)
    ).join(
        Building, Transaction.building_id == Building.id
    ).group_by(
        Building.building_type, Transaction.transaction_type
    ).all()

    by_transaction = {
        "아파트_매매": 0, "아파트_전월세": 0,
        "오피스텔_매매": 0, "오피스텔_전월세": 0,
        "빌라_매매": 0, "빌라_전월세": 0,
        "단독다가구_매매": 0, "단독다가구_전월세": 0
    }

    total_transactions = 0
    
    for b_type, t_type, count in transaction_counts:
        total_transactions += count
        
        k_type = type_map.get(b_type, "")
        if not k_type:
            continue
            
        k_trans = "매매" if t_type == TransactionType.SALE else "전월세"
        
        # 키 이름 매핑 (단독/다가구 -> 단독다가구)
        if k_type == "단독/다가구":
            k_type = "단독다가구"
            
        key = f"{k_type}_{k_trans}"
        if key in by_transaction:
            by_transaction[key] += count

    return {
        "total_properties": total_properties,
        "total_transactions": total_transactions,
        "by_type": by_type,
        "by_transaction": by_transaction
    }
