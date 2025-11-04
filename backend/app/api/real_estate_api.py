"""
부동산 데이터 API
지도 viewport 기반 부동산 조회 엔드포인트
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from app.db.postgre_db import get_db
from app.models.real_estate import RealEstate, Transaction, PropertyType, TransactionType

router = APIRouter(prefix="/api/real-estate", tags=["real-estate"])


# ============================================================================
# Response Models
# ============================================================================

class PropertyResponse(BaseModel):
    """부동산 응답 모델"""
    id: int
    code: str
    name: str = Field(alias="단지명")
    property_type: str = Field(alias="유형")
    latitude: float = Field(alias="위도")
    longitude: float = Field(alias="경도")

    # 기본 정보
    gu: str = Field(alias="구", default="")
    dong: str = Field(alias="동", default="")
    total_households: Optional[int] = Field(alias="세대수", default=None)
    total_buildings: Optional[int] = Field(alias="동수", default=None)
    completion_date: Optional[str] = Field(alias="준공년월", default=None)
    min_area: Optional[float] = Field(alias="minArea", default=None)
    max_area: Optional[float] = Field(alias="maxArea", default=None)

    # 거래 건수
    deal_count: int = Field(alias="매매_거래건수", default=0)
    lease_count: int = Field(alias="전세_거래건수", default=0)
    rent_count: int = Field(alias="월세_거래건수", default=0)
    total_article_count: int = Field(alias="총_거래건수", default=0)

    # 가격 정보 (만원 단위 - raw)
    매매_최저가: Optional[int] = None
    매매_최고가: Optional[int] = None
    전세_최저가: Optional[int] = None
    전세_최고가: Optional[int] = None
    월세_최저가: Optional[int] = None
    월세_최고가: Optional[int] = None

    # 가격 정보 (억원 단위 - 표시용)
    매매_최저가_억원: Optional[str] = None
    매매_최고가_억원: Optional[str] = None
    전세_최저가_억원: Optional[str] = None
    전세_최고가_억원: Optional[str] = None
    월세_최저가_억원: Optional[str] = None
    월세_최고가_억원: Optional[str] = None

    # 면적 요약
    면적요약: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


def format_eok(value: Optional[int]) -> str:
    """만원을 억원으로 변환"""
    if not value or value == 0:
        return ""
    try:
        eok = value / 10000
        return f"{eok:.1f}" if eok % 1 != 0 else f"{int(eok)}"
    except:
        return ""


def map_property_type_to_korean(property_type: PropertyType) -> str:
    """PropertyType Enum을 한글로 매핑"""
    mapping = {
        PropertyType.APARTMENT: "아파트",
        PropertyType.OFFICETEL: "오피스텔",
        PropertyType.ONEROOM: "원룸",
        PropertyType.VILLA: "빌라",
        PropertyType.HOUSE: "단독/다가구",
    }
    return mapping.get(property_type, "기타")


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/properties", response_model=List[PropertyResponse])
async def get_properties(
    # Viewport bounds
    south: float = Query(..., description="남쪽 위도 (viewport 하단)"),
    north: float = Query(..., description="북쪽 위도 (viewport 상단)"),
    west: float = Query(..., description="서쪽 경도 (viewport 좌측)"),
    east: float = Query(..., description="동쪽 경도 (viewport 우측)"),

    # Zoom level for optimization
    zoom: Optional[int] = Query(None, description="지도 줌 레벨 (1-14)"),

    # Filters
    property_types: Optional[str] = Query(None, description="부동산 유형 (쉼표로 구분: apartment,officetel,villa,oneroom,house)"),
    transaction_type: Optional[str] = Query(None, description="거래 유형 (sale, jeonse, rent)"),
    min_price: Optional[int] = Query(None, description="최소 가격 (억원)"),
    max_price: Optional[int] = Query(None, description="최대 가격 (억원)"),

    # Pagination
    limit: int = Query(1000, le=10000, description="최대 결과 수"),
    offset: int = Query(0, description="결과 오프셋"),

    db: Session = Depends(get_db)
):
    """
    지도 viewport 기반 부동산 조회

    **성능 최적화:**
    - Viewport 경계로 필터링하여 필요한 데이터만 조회
    - Zoom level에 따라 결과 수 제한
    - 인덱스를 활용한 빠른 조회 (lat/lon)

    **필터링:**
    - 부동산 유형, 거래 유형, 가격 범위
    """

    # 기본 쿼리: viewport 내의 부동산 (eager loading으로 최적화)
    from sqlalchemy.orm import joinedload

    query = db.query(RealEstate).options(
        joinedload(RealEstate.region),
        joinedload(RealEstate.transactions)
    ).filter(
        and_(
            RealEstate.latitude.between(south, north),
            RealEstate.longitude.between(west, east)
        )
    )

    # 부동산 유형 필터
    if property_types:
        type_list = []
        for pt in property_types.split(','):
            pt = pt.strip().upper()
            if hasattr(PropertyType, pt):
                type_list.append(getattr(PropertyType, pt))
        if type_list:
            query = query.filter(RealEstate.property_type.in_(type_list))

    # 거래 유형 및 가격 필터 (Transaction 조인 필요)
    if transaction_type or min_price or max_price:
        query = query.join(Transaction, RealEstate.id == Transaction.real_estate_id)

        if transaction_type:
            if transaction_type.lower() == "sale":
                query = query.filter(Transaction.transaction_type == TransactionType.SALE)
                if min_price:
                    query = query.filter(Transaction.max_sale_price >= min_price * 10000)
                if max_price:
                    query = query.filter(Transaction.min_sale_price <= max_price * 10000)

            elif transaction_type.lower() == "jeonse":
                query = query.filter(Transaction.transaction_type == TransactionType.JEONSE)
                if min_price:
                    query = query.filter(Transaction.max_deposit >= min_price * 10000)
                if max_price:
                    query = query.filter(Transaction.min_deposit <= max_price * 10000)

            elif transaction_type.lower() == "rent":
                query = query.filter(Transaction.transaction_type == TransactionType.RENT)
                if min_price:
                    query = query.filter(Transaction.max_monthly_rent >= min_price * 10000)
                if max_price:
                    query = query.filter(Transaction.min_monthly_rent <= max_price * 10000)

    # Zoom level에 따른 limit 조정
    if zoom:
        if zoom >= 7:
            limit = min(limit, 500)
        elif zoom >= 5:
            limit = min(limit, 1000)
        elif zoom >= 3:
            limit = min(limit, 2000)

    # 페이지네이션 및 실행
    query = query.distinct().limit(limit).offset(offset)
    real_estates = query.all()

    # 각 부동산의 가격 정보 조회 (이미 eager loading으로 가져온 데이터 사용)
    result = []
    for re in real_estates:
        # 지역 정보 추출
        region_parts = re.region.name.split() if re.region else ["", ""]
        gu = region_parts[0] if len(region_parts) > 0 else ""
        dong = region_parts[1] if len(region_parts) > 1 else ""

        # Transaction 데이터에서 가격 정보 추출 (이미 joinedload로 가져온 데이터)
        매매_최저가 = None
        매매_최고가 = None
        전세_최저가 = None
        전세_최고가 = None
        월세_최저가 = None
        월세_최고가 = None

        for trans in re.transactions:
            if trans.transaction_type == TransactionType.SALE:
                매매_최저가 = trans.min_sale_price if trans.min_sale_price else None
                매매_최고가 = trans.max_sale_price if trans.max_sale_price else None
            elif trans.transaction_type == TransactionType.JEONSE:
                전세_최저가 = trans.min_deposit if trans.min_deposit else None
                전세_최고가 = trans.max_deposit if trans.max_deposit else None
            elif trans.transaction_type == TransactionType.RENT:
                월세_최저가 = trans.min_monthly_rent if trans.min_monthly_rent else None
                월세_최고가 = trans.max_monthly_rent if trans.max_monthly_rent else None

        # 응답 데이터 구성
        property_data = PropertyResponse(
            id=re.id,
            code=re.code,
            단지명=re.name,
            유형=map_property_type_to_korean(re.property_type),
            위도=float(re.latitude),
            경도=float(re.longitude),
            구=gu,
            동=dong,
            세대수=re.total_households,
            동수=re.total_buildings,
            준공년월=re.completion_date,
            minArea=re.min_exclusive_area,
            maxArea=re.max_exclusive_area,
            매매_거래건수=re.deal_count,
            전세_거래건수=re.lease_count,
            월세_거래건수=re.rent_count,
            총_거래건수=re.deal_count + re.lease_count + re.rent_count,
            매매_최저가=매매_최저가,
            매매_최고가=매매_최고가,
            전세_최저가=전세_최저가,
            전세_최고가=전세_최고가,
            월세_최저가=월세_최저가,
            월세_최고가=월세_최고가,
            매매_최저가_억원=format_eok(매매_최저가),
            매매_최고가_억원=format_eok(매매_최고가),
            전세_최저가_억원=format_eok(전세_최저가),
            전세_최고가_억원=format_eok(전세_최고가),
            월세_최저가_억원=format_eok(월세_최저가),
            월세_최고가_억원=format_eok(월세_최고가),
            면적요약=f"{re.min_exclusive_area}-{re.max_exclusive_area}㎡" if re.min_exclusive_area else ""
        )

        result.append(property_data)

    return result


@router.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    부동산 데이터 통계
    """
    total_properties = db.query(RealEstate).count()
    total_transactions = db.query(Transaction).count()

    # 유형별 통계
    type_stats = {}
    for prop_type in PropertyType:
        count = db.query(RealEstate).filter(RealEstate.property_type == prop_type).count()
        type_stats[map_property_type_to_korean(prop_type)] = count

    return {
        "total_properties": total_properties,
        "total_transactions": total_transactions,
        "by_type": type_stats
    }
