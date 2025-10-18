from pydantic import BaseModel, Field
from datetime import datetime 
from decimal import Decimal

# TrustScore Schemas

class TrustScoreBase(BaseModel):
    real_estate_id: int = Field(..., description="부동산ID")
    score: Decimal = Field(..., ge=0, le=100, decimal_places=2,
                            description="부동산 매물 신뢰도점수")
    verification_notes: str|None = Field(None, description="검증 내용")


class TrustScoreCreate(TrustScoreBase):
    pass

class TrustScoreUpdate(BaseModel):
    score: Decimal|None = Field(None, ge=0, le=100, decimal_places=2, 
                                description="부동산 매물 신뢰점수")
    verification_notes: str|None = Field(None, description="검증 내용")
    
class TrustScoreResponse(TrustScoreBase):
    id: int = Field(..., description="신뢰점수 ID")
    calculated_at: datetime = Field(..., description="계산일자")
    updated_at: datetime|None = Field(None, description="수정일")
    
    class Config:
        from_attributes = True