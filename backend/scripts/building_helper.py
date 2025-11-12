"""
Building 테이블 헬퍼 함수
부동산 데이터 수집 시 Building 테이블을 활용하기 위한 유틸리티 함수들
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.enums import PropertyType


def get_or_create_building(
    db: Session,
    building_type: PropertyType,
    name: str,
    address: str,
    region_id: int,
    region_name: Optional[str] = None,
    road_address: Optional[str] = None,
    build_year: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    total_households: Optional[int] = None,
    nearby_subway_stations: Optional[str] = None,
    nearby_schools: Optional[str] = None,
    nearby_marts: Optional[str] = None,
) -> Tuple[Building, bool]:
    """
    Building 객체를 조회하거나 생성합니다.

    Args:
        db: Database session
        building_type: 건물 유형 (PropertyType enum)
        name: 건물명
        address: 지번 주소
        region_id: 지역 ID
        ... (기타 Building 필드)

    Returns:
        (Building 객체, 생성 여부) 튜플
        - created=True: 새로 생성됨
        - created=False: 기존 데이터 조회됨
    """
    # 기존 Building 조회 (주소와 건물명으로)
    building = db.query(Building).filter(
        Building.building_type == building_type,
        Building.address == address,
        Building.name == name,
    ).first()

    if building:
        # 기존 Building이 있으면 반환
        return (building, False)

    # 새 Building 생성
    building = Building(
        building_type=building_type,
        name=name,
        build_year=build_year,
        total_households=total_households,
        region_id=region_id,
        region_name=region_name,
        address=address,
        road_address=road_address,
        latitude=latitude,
        longitude=longitude,
        nearby_subway_stations=nearby_subway_stations,
        nearby_schools=nearby_schools,
        nearby_marts=nearby_marts,
    )

    db.add(building)
    db.flush()  # ID 생성을 위해 flush

    return (building, True)


def update_building_facilities(
    db: Session,
    building: Building,
    nearby_subway_stations: Optional[str] = None,
    nearby_schools: Optional[str] = None,
    nearby_marts: Optional[str] = None,
) -> None:
    """
    Building의 주변 시설 정보를 업데이트합니다.

    Args:
        db: Database session
        building: Building 객체
        nearby_subway_stations: 주변 지하철역 정보 (JSON)
        nearby_schools: 주변 학교 정보 (JSON)
        nearby_marts: 주변 마트 정보 (JSON)
    """
    updated = False

    if nearby_subway_stations and not building.nearby_subway_stations:
        building.nearby_subway_stations = nearby_subway_stations
        updated = True

    if nearby_schools and not building.nearby_schools:
        building.nearby_schools = nearby_schools
        updated = True

    if nearby_marts and not building.nearby_marts:
        building.nearby_marts = nearby_marts
        updated = True

    if updated:
        db.flush()
