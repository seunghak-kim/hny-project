"""Transaction common schemas and types"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enum"""
    SALE = "sale"
    RENT = "rent"
    MONTHLY_RENT = "monthly_rent"
    JEONSE = "jeonse"


class ContractType(str, Enum):
    """Contract type enum"""
    NEW = "new"
    RENEWAL = "renewal"


class DealingType(str, Enum):
    """Dealing type enum"""
    DIRECT = "direct"
    BROKERAGE = "brokerage"


class TransactionBase(BaseModel):
    """Base transaction information (common fields for all transaction types)"""
    region_id: int = Field(..., description="Region ID")
    deal_year: str = Field(..., max_length=4, description="Deal year")
    deal_month: str = Field(..., max_length=2, description="Deal month")
    deal_day: str = Field(..., max_length=2, description="Deal day")
    transaction_date: datetime = Field(..., description="Transaction date")


class SaleTransactionBase(TransactionBase):
    """Common fields for sale transactions"""
    deal_amount: int = Field(..., description="Deal amount (10,000 KRW)")
    deal_type: Optional[str] = Field(None, max_length=20, description="Deal type")
    cancel_deal_day: Optional[str] = Field(None, max_length=8, description="Cancel deal day")
    dealing_gbn: Optional[str] = Field(None, max_length=20, description="Dealing type")
    estate_agent_sgg_nm: Optional[str] = Field(None, max_length=50, description="Estate agent location")
    seller_gbn: Optional[str] = Field(None, max_length=10, description="Seller type")
    buyer_gbn: Optional[str] = Field(None, max_length=10, description="Buyer type")


class RentTransactionBase(TransactionBase):
    """Common fields for rent transactions"""
    deposit: int = Field(..., description="Deposit (10,000 KRW)")
    monthly_rent: int = Field(0, description="Monthly rent (10,000 KRW)")
    contract_term: Optional[str] = Field(None, max_length=50, description="Contract term")
    contract_type: Optional[str] = Field(None, max_length=20, description="Contract type")
    use_rr_right: Optional[str] = Field(None, max_length=20, description="Renewal right usage")
    pre_deposit: Optional[int] = Field(None, description="Previous deposit (10,000 KRW)")
    pre_monthly_rent: Optional[int] = Field(None, description="Previous monthly rent (10,000 KRW)")


class TransactionResponse(BaseModel):
    """Common transaction response fields"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Transaction statistics schemas
class TransactionStats(BaseModel):
    """Transaction statistics"""
    total_count: int = Field(..., description="Total transaction count")
    avg_price: Optional[float] = Field(None, description="Average price (10,000 KRW)")
    min_price: Optional[int] = Field(None, description="Minimum price (10,000 KRW)")
    max_price: Optional[int] = Field(None, description="Maximum price (10,000 KRW)")
    recent_transaction_date: Optional[datetime] = Field(None, description="Recent transaction date")


class SaleTransactionStats(TransactionStats):
    """Sale transaction statistics"""
    pass


class RentTransactionStats(BaseModel):
    """Rent transaction statistics"""
    total_count: int = Field(..., description="Total transaction count")
    avg_deposit: Optional[float] = Field(None, description="Average deposit (10,000 KRW)")
    avg_monthly_rent: Optional[float] = Field(None, description="Average monthly rent (10,000 KRW)")
    min_deposit: Optional[int] = Field(None, description="Minimum deposit (10,000 KRW)")
    max_deposit: Optional[int] = Field(None, description="Maximum deposit (10,000 KRW)")
    recent_transaction_date: Optional[datetime] = Field(None, description="Recent transaction date")


# Transaction filter schemas
class TransactionFilter(BaseModel):
    """Transaction filter"""
    region_id: Optional[int] = Field(None, description="Region ID")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    min_price: Optional[int] = Field(None, description="Minimum price (10,000 KRW)")
    max_price: Optional[int] = Field(None, description="Maximum price (10,000 KRW)")
    min_area: Optional[float] = Field(None, description="Minimum area (sqm)")
    max_area: Optional[float] = Field(None, description="Maximum area (sqm)")


class SaleTransactionFilter(TransactionFilter):
    """Sale transaction filter"""
    deal_type: Optional[str] = Field(None, description="Deal type")


class RentTransactionFilter(TransactionFilter):
    """Rent transaction filter"""
    contract_type: Optional[str] = Field(None, description="Contract type")
    min_monthly_rent: Optional[int] = Field(None, description="Minimum monthly rent (10,000 KRW)")
    max_monthly_rent: Optional[int] = Field(None, description="Maximum monthly rent (10,000 KRW)")
