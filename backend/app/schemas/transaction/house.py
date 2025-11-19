from pydantic import Field, BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class HouseSaleTransaction(BaseModel):
    total_floor_area:Optional[Decimal] = Field(None, description="연면적")
    plottage_area:Optional[Decimal] = Field(None, description="대지면적")
    

class HouseSaleTransactionCreate(HouseSaleTransaction):
    pass

class HouseSaleTransactionUpdate(HouseSaleTransaction):
    total_floor_area:Optional[Decimal] = Field(None, description="연면적")
    plottage_area:Optional[Decimal] = Field(None, description="대지면적")

class HouseSaleTransactionResponse(HouseSaleTransaction):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

