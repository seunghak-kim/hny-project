from pydantic import Field, BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class VillaSaleTransaction(BaseModel):
    land_area:Optional[Decimal] = Field(None, description="대지권면적")
    

class VillaSaleTransactionCreate(VillaSaleTransaction):
    pass

class VillaSaleTransactionUpdate(VillaSaleTransaction):
    land_area:Optional[Decimal] = Field(None, description="대지권면적")

class VillaSaleTransactionResponse(VillaSaleTransaction):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

