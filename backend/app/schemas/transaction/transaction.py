from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime 
from decimal import Decimal
from app.models.enums import TransactionType

class TransactionBase(BaseModel):
    """거래 기본 스키마"""
    transaction_type: TransactionType = Field(..., description="거래유형: 매매, 전/월세")
    exclusive_area:Optional[Decimal] = Field(None, description="전용면적")
    floor:Optional[int] = Field(None, description="층")
    trans_date: Optional[datetime] = Field(None, description="거래일자")
    
    # 건물 id 
    building_id:int = Field(..., description="건물 id")
    
    
class CreateTransactionRequest(TransactionBase):
    """거래 생성 요청 스키마"""
    pass
    
    
class UpdateTransactionRequest(TransactionBase):
    """거래 업데이트 요청 스키마"""

    transaction_type: Optional[TransactionType] = Field(None, description="거래유형: 매매, 전/월세")
    exclusive_area:Optional[Decimal] = Field(None, description="전용면적")
    floor:Optional[int] = Field(None, description="층")
    trans_date: Optional[datetime] = Field(None, description="거래일자")


class TransactionResponse(TransactionBase):
    """거래 응답 스키마"""
    id: int = Field(..., description="거래 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")

    class Config:
        from_attributes = True