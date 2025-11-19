from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class SaleTransactionBase(BaseModel):
    """매매 거래 기본 스키마"""
    deal_amount: Decimal = Field(..., description="매매 금액")
    cdeal_type: Optional[str] = Field(None, description="거래 유형 ex: 직거래, 중개거래")
    cdeal_day: Optional[str] = Field(None, description="해제사유발생일 (거래 해제 시)")
    dealing_gbn: Optional[str] = Field(None, description="거래구분")
    estate_agent_sgg_nm: Optional[str] = Field(None, description="부동산중개소 시군구명")
    saler_gbn: Optional[str] = Field(None, description="판매구분")
    buyer_gbn: Optional[str] = Field(None, description="구매구분")
    transaction_id: int = Field(..., description="거래 ID")

class SaleTransactionCreate(SaleTransactionBase):
    """매매 거래 생성 스키마"""
    pass

class SaleTransactionUpdate(SaleTransactionBase):
    """매매 거래 업데이트 스키마"""
    deal_amount: Optional[Decimal] = Field(None, description="매매 금액")

class SaleTransactionResponse(SaleTransactionBase):
    """매매 거래 응답 스키마"""
    id: int = Field(..., description="매매 거래 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")

    class Config:
        from_attributes = True