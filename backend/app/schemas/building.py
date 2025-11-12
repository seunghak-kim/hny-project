"""Building (건축물 통합 정보) 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.enums import PropertyType


# ===== Building Base Schemas =====
class BuildingBase(BaseModel):
    """건축물 기본 스키마"""
    building_type: PropertyType = Field(..., description="건물 유형 (아파트/오피스텔/단독/연립)")
    name: Optional[str] = Field(None, max_length=100, description="건물명")
    build_year: Optional[str] = Field(None, max_length=4, description="건축년도")
    total_households: Optional[int] = Field(None, description="총 세대수")

    # 지역 정보
    region_id: int = Field(..., description="지역 ID") # 시군구 코드 
    region_name: Optional[str] = Field(None, max_length=50, description="읍면동명")

    # 주소 정보
    address: str = Field(..., max_length=255, description="지번 주소")
    road_address: Optional[str] = Field(None, max_length=255, description="도로명 주소")

    # 위치 정보
    latitude: Optional[Decimal] = Field(None, description="위도")
    longitude: Optional[Decimal] = Field(None, description="경도")

    # 주변 시설 정보
    nearby_subway_stations: Optional[str] = Field(None, description="1km 이내 지하철역 정보(JSON)")
    nearby_schools: Optional[str] = Field(None, description="인근 초중고 정보(JSON)")
    nearby_marts: Optional[str] = Field(None, description="인근 마트 정보(JSON)")


class BuildingCreate(BuildingBase):
    """건축물 생성 스키마"""
    pass


class BuildingUpdate(BaseModel):
    """건축물 업데이트 스키마"""
    building_type: Optional[PropertyType] = Field(None, description="건물 유형")
    name: Optional[str] = Field(None, max_length=100, description="건물명")
    build_year: Optional[str] = Field(None, max_length=4, description="건축년도")
    total_households: Optional[int] = Field(None, description="총 세대수")
    region_id: Optional[int] = Field(None, description="지역 ID")
    region_name: Optional[str] = Field(None, max_length=50, description="읍면동명")
    address: Optional[str] = Field(None, max_length=255, description="지번 주소")
    road_address: Optional[str] = Field(None, max_length=255, description="도로명 주소")
    latitude: Optional[Decimal] = Field(None, description="위도")
    longitude: Optional[Decimal] = Field(None, description="경도")
    nearby_subway_stations: Optional[str] = Field(None, description="1km 이내 지하철역 정보(JSON)")
    nearby_schools: Optional[str] = Field(None, description="인근 초중고 정보(JSON)")
    nearby_marts: Optional[str] = Field(None, description="인근 마트 정보(JSON)")


class BuildingResponse(BuildingBase):
    """건축물 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Building with Details =====
class BuildingWithDetails(BuildingResponse):
    """상세 정보를 포함한 건축물 응답 스키마"""
    # 타입별 상세 정보를 optional로 포함
    # 실제 사용시에는 building_type에 따라 해당하는 정보만 채워짐
    apartment_details: Optional[dict] = Field(None, description="아파트 상세 정보")
    house_details: Optional[dict] = Field(None, description="단독/다가구 상세 정보")
    villa_details: Optional[dict] = Field(None, description="연립/다세대 상세 정보")
    officetel_details: Optional[dict] = Field(None, description="오피스텔 상세 정보")

    class Config:
        from_attributes = True


# ===== Building Search/Filter Schemas =====
class BuildingFilter(BaseModel):
    """건축물 검색 필터"""
    building_type: Optional[PropertyType] = Field(None, description="건물 유형")
    region_id: Optional[int] = Field(None, description="지역 ID")
    min_build_year: Optional[str] = Field(None, description="최소 건축년도")
    max_build_year: Optional[str] = Field(None, description="최대 건축년도")
    min_latitude: Optional[Decimal] = Field(None, description="최소 위도")
    max_latitude: Optional[Decimal] = Field(None, description="최대 위도")
    min_longitude: Optional[Decimal] = Field(None, description="최소 경도")
    max_longitude: Optional[Decimal] = Field(None, description="최대 경도")
    has_subway: Optional[bool] = Field(None, description="지하철역 1km 이내 여부")
    keyword: Optional[str] = Field(None, description="건물명/주소 검색 키워드")


class BuildingListResponse(BaseModel):
    """건축물 목록 응답 스키마"""
    total: int = Field(..., description="전체 건축물 수")
    items: list[BuildingResponse] = Field(..., description="건축물 목록")
    page: int = Field(1, description="현재 페이지")
    size: int = Field(20, description="페이지 크기")

    class Config:
        from_attributes = True
