from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime 
from decimal import Decimal

class ApartmentSaleTransaction(BaseModel):
    apt_dong: int = Field(..., description="아파트 동")
    land_leasehold_gbn: str = Field(..., description="토지임대여부")
    rgst_date: datetime = Field(..., description="거래 등록일자")
    
    
class ApartmentSaleTransactionCreate(ApartmentSaleTransaction):
    pass

class ApartmentSaleTransactionUpdate(BaseModel):
    apt_dong: Optional[int] = Field(None, description="아파트 동")
    land_leasehold_gbn: Optional[str] = Field(None, description="토지임대여부")
    rgst_date: Optional[datetime] = Field(None, description="거래 등록일자")

class ApartmentSaleTransactionResponse(ApartmentSaleTransaction):
    id: int = Field(..., description="거래 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    
    class Config:
        from_attributes = True

    