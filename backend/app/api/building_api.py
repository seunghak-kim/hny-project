"""
건축물 통합 정보 API
Building 테이블을 사용한 건물 정보 조회 엔드포인트
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.db.postgre_db import get_db
from app.models.building import Building
from app.models.enums import PropertyType
from app.schemas.building import (
    BuildingResponse,
    BuildingWithDetails,
    BuildingFilter,
    BuildingListResponse,
    BuildingCreate,
    BuildingUpdate,
)

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


# ============================================================================
# GET /api/buildings - 건물 목록 조회
# ============================================================================

@router.get("", response_model=BuildingListResponse)
async def get_buildings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    building_type: Optional[PropertyType] = Query(None, description="건물 유형"),
    region_id: Optional[int] = Query(None, description="지역 ID"),
    min_build_year: Optional[str] = Query(None, description="최소 건축년도"),
    max_build_year: Optional[str] = Query(None, description="최대 건축년도"),
    keyword: Optional[str] = Query(None, description="건물명/주소 검색"),
    has_subway: Optional[bool] = Query(None, description="지하철역 1km 이내 여부"),
):
    """
    건물 목록 조회

    - 페이징 지원
    - 건물 타입, 지역, 건축년도, 키워드 등으로 필터링 가능
    """
    # 기본 쿼리
    query = db.query(Building)

    # 필터 적용
    filters = []

    if building_type:
        filters.append(Building.building_type == building_type)

    if region_id:
        filters.append(Building.region_id == region_id)

    if min_build_year:
        filters.append(Building.build_year >= min_build_year)

    if max_build_year:
        filters.append(Building.build_year <= max_build_year)

    if keyword:
        filters.append(
            or_(
                Building.name.ilike(f"%{keyword}%"),
                Building.address.ilike(f"%{keyword}%"),
            )
        )

    if has_subway is not None:
        if has_subway:
            filters.append(Building.nearby_subway_stations.isnot(None))
            filters.append(Building.nearby_subway_stations != "")
        else:
            filters.append(
                or_(
                    Building.nearby_subway_stations.is_(None),
                    Building.nearby_subway_stations == "",
                )
            )

    if filters:
        query = query.filter(and_(*filters))

    # 전체 개수
    total = query.count()

    # 페이징
    offset = (page - 1) * size
    buildings = query.offset(offset).limit(size).all()

    return BuildingListResponse(
        total=total,
        items=[BuildingResponse.model_validate(b) for b in buildings],
        page=page,
        size=size,
    )


# ============================================================================
# GET /api/buildings/{building_id} - 건물 상세 조회
# ============================================================================

@router.get("/{building_id}", response_model=BuildingWithDetails)
async def get_building_detail(
    building_id: int,
    db: Session = Depends(get_db),
):
    """
    건물 상세 정보 조회

    - Building 기본 정보
    - 해당 타입의 상세 정보 포함 (Apartment, House, Villa, Officetel)
    """
    # Building 조회
    building = db.query(Building).filter(Building.id == building_id).first()

    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # 타입별 상세 정보 조회 (현재 모델 변경으로 인해 상세 정보는 제공하지 않음)
    details = {}

    # 응답 생성
    building_dict = {
        "id": building.id,
        "building_type": building.building_type,
        "name": building.name,
        "build_year": building.build_year,
        "total_households": building.total_households,
        "region_id": building.region_id,
        "region_name": building.region.gu_name if building.region else None,
        "address": building.address,
        # "road_address": building.road_address, # Building model doesn't have road_address in the file I saw earlier? checking...
        "latitude": building.latitude,
        "longitude": building.longitude,
        # "nearby_subway_stations": building.nearby_subway_stations, # These are in Infrastructure now?
        # "nearby_schools": building.nearby_schools,
        # "nearby_marts": building.nearby_marts,
        "created_at": building.created_at,
        "updated_at": building.updated_at,
        **details,
    }
    
    # Infrastructure 정보 추가 (Building 모델에 relationship이 있다면)
    if hasattr(building, 'infrastructures') and building.infrastructures:
        # infrastructures is a list or single? relationship says "infrastructures" but back_populates="building".
        # Usually one-to-one or one-to-many. Let's check Building model again.
        # Building model: infrastructures = relationship("Infrastructure", back_populates="building", cascade="all, delete-orphan")
        # It seems to be a list. But Infrastructure has unique building_id. So it's one-to-one effectively but mapped as list by default unless uselist=False.
        # Let's assume it might be a list.
        infra = building.infrastructures[0] if building.infrastructures else None
        if infra:
             building_dict["nearby_subway_stations"] = infra.nearby_subway_stations
             building_dict["nearby_schools"] = infra.nearby_schools
             building_dict["nearby_marts"] = infra.nearby_marts

    return BuildingWithDetails(**building_dict)


# ============================================================================
# GET /api/buildings/search/nearby - 주변 건물 검색
# ============================================================================

@router.get("/search/nearby", response_model=List[BuildingResponse])
async def search_nearby_buildings(
    latitude: float = Query(..., description="중심 위도"),
    longitude: float = Query(..., description="중심 경도"),
    radius_km: float = Query(1.0, ge=0.1, le=10.0, description="반경 (km)"),
    building_type: Optional[PropertyType] = Query(None, description="건물 유형"),
    limit: int = Query(20, ge=1, le=100, description="최대 결과 수"),
    db: Session = Depends(get_db),
):
    """
    특정 좌표 주변 건물 검색

    - Haversine 공식 사용 (위도/경도 기반 거리 계산)
    - 반경 내 건물 조회
    """
    # 위도/경도를 라디안으로 변환하여 거리 계산
    # Haversine formula
    distance_formula = func.acos(
        func.cos(func.radians(latitude))
        * func.cos(func.radians(Building.latitude))
        * func.cos(func.radians(Building.longitude) - func.radians(longitude))
        + func.sin(func.radians(latitude)) * func.sin(func.radians(Building.latitude))
    ) * 6371  # 지구 반지름 (km)

    query = db.query(Building).filter(
        Building.latitude.isnot(None),
        Building.longitude.isnot(None),
        distance_formula <= radius_km,
    )

    if building_type:
        query = query.filter(Building.building_type == building_type)

    buildings = query.limit(limit).all()

    return [BuildingResponse.model_validate(b) for b in buildings]


# ============================================================================
# GET /api/buildings/search/bbox - 지도 영역 내 건물 검색
# ============================================================================

@router.get("/search/bbox", response_model=List[BuildingResponse])
async def search_buildings_in_bbox(
    min_lat: float = Query(..., description="최소 위도"),
    max_lat: float = Query(..., description="최대 위도"),
    min_lng: float = Query(..., description="최소 경도"),
    max_lng: float = Query(..., description="최대 경도"),
    building_type: Optional[PropertyType] = Query(None, description="건물 유형"),
    limit: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
    db: Session = Depends(get_db),
):
    """
    지도 bounding box 내 건물 검색

    - 지도 뷰포트 기반 건물 조회
    """
    query = db.query(Building).filter(
        Building.latitude.between(min_lat, max_lat),
        Building.longitude.between(min_lng, max_lng),
    )

    if building_type:
        query = query.filter(Building.building_type == building_type)

    buildings = query.limit(limit).all()

    return [BuildingResponse.model_validate(b) for b in buildings]


# ============================================================================
# POST /api/buildings - 건물 생성
# ============================================================================

@router.post("", response_model=BuildingResponse, status_code=201)
async def create_building(
    building_data: BuildingCreate,
    db: Session = Depends(get_db),
):
    """
    새 건물 생성
    """
    # Building 생성
    building = Building(
        building_type=building_data.building_type,
        name=building_data.name,
        build_year=building_data.build_year,
        total_households=building_data.total_households,
        region_id=building_data.region_id,
        # region_name=building_data.region_name,
        address=building_data.address,
        # road_address=building_data.road_address,
        latitude=building_data.latitude,
        longitude=building_data.longitude,
        nearby_subway_stations=building_data.nearby_subway_stations,
        nearby_schools=building_data.nearby_schools,
        nearby_marts=building_data.nearby_marts,
    )

    db.add(building)
    db.commit()
    db.refresh(building)

    return BuildingResponse.model_validate(building)


# ============================================================================
# PATCH /api/buildings/{building_id} - 건물 정보 수정
# ============================================================================

@router.patch("/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: int,
    building_data: BuildingUpdate,
    db: Session = Depends(get_db),
):
    """
    건물 정보 수정
    """
    building = db.query(Building).filter(Building.id == building_id).first()

    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # 수정할 필드만 업데이트
    update_data = building_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(building, field, value)

    db.commit()
    db.refresh(building)

    return BuildingResponse.model_validate(building)


# ============================================================================
# DELETE /api/buildings/{building_id} - 건물 삭제
# ============================================================================

@router.delete("/{building_id}", status_code=204)
async def delete_building(
    building_id: int,
    db: Session = Depends(get_db),
):
    """
    건물 삭제
    """
    building = db.query(Building).filter(Building.id == building_id).first()

    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    db.delete(building)
    db.commit()

    return None


# ============================================================================
# GET /api/buildings/stats - 건물 통계
# ============================================================================

@router.get("/stats/summary")
async def get_building_stats(
    db: Session = Depends(get_db),
):
    """
    건물 통계 정보

    - 타입별 건물 수
    - 지역별 건물 수
    """
    # 타입별 통계
    type_stats = (
        db.query(
            Building.building_type,
            func.count(Building.id).label("count"),
        )
        .group_by(Building.building_type)
        .all()
    )

    # 지역별 통계 (상위 10개)
    from app.models.region import Region
    region_stats = (
        db.query(
            Region.gu_name.label("region_name"),
            func.count(Building.id).label("count"),
        )
        .join(Region, Building.region_id == Region.id)
        .filter(Region.gu_name.isnot(None))
        .group_by(Region.gu_name)
        .order_by(func.count(Building.id).desc())
        .limit(10)
        .all()
    )

    # 전체 통계
    total_count = db.query(func.count(Building.id)).scalar()
    buildings_with_coords = db.query(func.count(Building.id)).filter(
        Building.latitude.isnot(None),
        Building.longitude.isnot(None),
    ).scalar()

    return {
        "total_buildings": total_count,
        "buildings_with_coordinates": buildings_with_coords,
        "by_type": {
            stat.building_type.value: stat.count for stat in type_stats
        },
        "top_regions": [
            {"region": stat.region_name, "count": stat.count}
            for stat in region_stats
        ],
    }
