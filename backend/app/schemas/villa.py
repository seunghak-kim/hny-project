"""연립/다세대 관련 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ===== Villa Base Schemas =====
class VillaBase(BaseModel):
    """연립/다세대 기본 스키마"""
    building_id: Optional[int] = Field(None, description="건물 ID (통합 건축물 정보)")
    property_code: str = Field(..., max_length=150, description="매물코드")
    name: str = Field(..., max_length=100, description="주택명")

class VillaCreate(VillaBase):
    """연립/다세대 생성 스키마"""
    pass


class VillaUpdate(BaseModel):
    """연립/다세대 업데이트 스키마"""
    building_id: Optional[int] = Field(None, description="건물 ID (통합 건축물 정보)")
    name: Optional[str] = Field(None, max_length=100, description="주택명")
    
class VillaResponse(VillaBase):
    """연립/다세대 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Villa Sale Transaction Schemas =====
class VillaSaleTransactionBase(BaseModel):
    """연립/다세대 매매 거래 기본 스키마"""
    villa_id: int = Field(..., description="연립/다세대 ID")
    region_id: int = Field(..., description="지역 ID")
    deal_year: str = Field(..., max_length=4, description="거래년도")
    deal_month: str = Field(..., max_length=2, description="거래월")
    deal_day: str = Field(..., max_length=2, description="거래일")
    transaction_date: datetime = Field(..., description="거래일")
    deal_amount: int = Field(..., description="거래금액(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    land_area: Optional[float] = Field(None, description="대지권면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    registration_date: Optional[str] = Field(None, max_length=8, description="등록일자")
    deal_type: Optional[str] = Field(None, max_length=20, description="거래유형")
    cancel_deal_day: Optional[str] = Field(None, max_length=8, description="해제사유발생일")
    dealing_gbn: Optional[str] = Field(None, max_length=20, description="거래구분")
    estate_agent_sgg_nm: Optional[str] = Field(None, max_length=50, description="중개사무소 소재지")
    seller_gbn: Optional[str] = Field(None, max_length=10, description="매도자 구분")
    buyer_gbn: Optional[str] = Field(None, max_length=10, description="매수자 구분")


class VillaSaleTransactionCreate(VillaSaleTransactionBase):
    """연립/다세대 매매 거래 생성 스키마"""
    pass


class VillaSaleTransactionUpdate(BaseModel):
    """연립/다세대 매매 거래 업데이트 스키마"""
    deal_amount: Optional[int] = Field(None, description="거래금액(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    land_area: Optional[float] = Field(None, description="대지권면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    registration_date: Optional[str] = Field(None, max_length=8, description="등록일자")
    deal_type: Optional[str] = Field(None, max_length=20, description="거래유형")
    cancel_deal_day: Optional[str] = Field(None, max_length=8, description="해제사유발생일")
    dealing_gbn: Optional[str] = Field(None, max_length=20, description="거래구분")
    estate_agent_sgg_nm: Optional[str] = Field(None, max_length=50, description="중개사무소 소재지")
    seller_gbn: Optional[str] = Field(None, max_length=10, description="매도자 구분")
    buyer_gbn: Optional[str] = Field(None, max_length=10, description="매수자 구분")


class VillaSaleTransactionResponse(VillaSaleTransactionBase):
    """연립/다세대 매매 거래 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Villa Rent Transaction Schemas =====
class VillaRentTransactionBase(BaseModel):
    """연립/다세대 전월세 거래 기본 스키마"""
    villa_id: int = Field(..., description="연립/다세대 ID")
    region_id: int = Field(..., description="지역 ID")
    deal_year: str = Field(..., max_length=4, description="계약년도")
    deal_month: str = Field(..., max_length=2, description="계약월")
    deal_day: str = Field(..., max_length=2, description="계약일")
    transaction_date: datetime = Field(..., description="계약일")
    deposit: int = Field(..., description="보증금(만원)")
    monthly_rent: int = Field(0, description="월세(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    contract_term: Optional[str] = Field(None, max_length=50, description="계약기간")
    contract_type: Optional[str] = Field(None, max_length=20, description="계약구분")
    use_rr_right: Optional[str] = Field(None, max_length=20, description="갱신요구권 사용여부")
    pre_deposit: Optional[int] = Field(None, description="종전 보증금(만원)")
    pre_monthly_rent: Optional[int] = Field(None, description="종전 월세(만원)")


class VillaRentTransactionCreate(VillaRentTransactionBase):
    """연립/다세대 전월세 거래 생성 스키마"""
    pass


class VillaRentTransactionUpdate(BaseModel):
    """연립/다세대 전월세 거래 업데이트 스키마"""
    deposit: Optional[int] = Field(None, description="보증금(만원)")
    monthly_rent: Optional[int] = Field(None, description="월세(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    contract_term: Optional[str] = Field(None, max_length=50, description="계약기간")
    contract_type: Optional[str] = Field(None, max_length=20, description="계약구분")
    use_rr_right: Optional[str] = Field(None, max_length=20, description="갱신요구권 사용여부")
    pre_deposit: Optional[int] = Field(None, description="종전 보증금(만원)")
    pre_monthly_rent: Optional[int] = Field(None, description="종전 월세(만원)")


class VillaRentTransactionResponse(VillaRentTransactionBase):
    """연립/다세대 전월세 거래 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Combined Schemas =====
class VillaWithTransactions(VillaResponse):
    """거래 내역을 포함한 연립/다세대 응답 스키마"""
    sale_transactions: list[VillaSaleTransactionResponse] = []
    rent_transactions: list[VillaRentTransactionResponse] = []

    class Config:
        from_attributes = True
