from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class RentTransaction(BaseModel):
    transaction_id:Optional[int] = Field(None, description="거래 ID")
    deposit:Optional[int] = Field(None, description="보증금")
    monthly_rent:Optional[int] = Field(None, description="월세")
    contract_term:str = Field(..., description="계약기간")
    contract_type:str = Field(..., description="계약유형")
    user_rr_right:str = Field(..., description="갱신요구권 사용 여부")
    pre_deposit:Optional[int] =  Field(None, description="종전 보증금")
    pre_monthly_rent:Optional[int] = Field(None, description="종전 월세")
    

class RentTransactionCreate(RentTransaction):
    pass

class RentTransactionUpdate(RentTransaction):
    deposit:Optional[int] = Field(None, description="보증금")
    monthly_rent:Optional[int] = Field(None, description="월세")
    
class RentTransactionResponse(RentTransaction):
    id: int = Field(..., description="전월세 거래 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")

    class Config:
        from_attributes = True
    