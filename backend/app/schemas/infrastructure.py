from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class InfrastructureBase(BaseModel):
    """인프라 기본 스키마"""
    building_id: int = Field(..., description="건물 ID")
    nearby_subway_stations: Optional[str] = Field(None, description="1km 이내 지하철역 정보(JSON)")
    nearby_schools: Optional[str] = Field(None, description="인근 초중고 정보(JSON)")
    nearby_marts: Optional[str] = Field(None, description="인근 마트 정보(JSON)")

class InfrastructureCreate(InfrastructureBase):
    """인프라 생성 스키마"""
    pass

class InfrastructureUpdate(BaseModel):
    """인프라 업데이트 스키마"""
    nearby_subway_stations: Optional[str] = Field(None, description="1km 이내 지하철역 정보(JSON)")
    nearby_schools: Optional[str] = Field(None, description="인근 초중고 정보(JSON)")
    nearby_marts: Optional[str] = Field(None, description="인근 마트 정보(JSON)")

class InfrastructureResponse(InfrastructureBase):
    """인프라 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True