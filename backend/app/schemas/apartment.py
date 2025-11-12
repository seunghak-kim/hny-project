"""아파트 관련 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ===== Apartment Base Schemas =====
class ApartmentBase(BaseModel):
    """아파트 기본 스키마"""
    building_id: Optional[int] = Field(None, description="건물 ID (통합 건축물 정보)")
    complex_code: str = Field(..., max_length=30, description="단지코드")
    name: str = Field(..., max_length=100, description="아파트 단지명")
    min_exclusive_area: Optional[float] = Field(None, description="최소 전용면적(제곱미터)")
    max_exclusive_area: Optional[float] = Field(None, description="최대 전용면적(제곱미터)")
    total_households: Optional[int] = Field(None, description="총 세대수")
    total_dong: Optional[int] = Field(None, description="총 동수")


class ApartmentCreate(ApartmentBase):
    """아파트 생성 스키마"""
    pass


class ApartmentUpdate(BaseModel):
    """아파트 업데이트 스키마"""
    building_id: Optional[int] = Field(None, description="건물 ID (통합 건축물 정보)")
    complex_code: Optional[str] = Field(None, max_length=30, description="단지코드")
    name: Optional[str] = Field(None, max_length=100, description="아파트 단지명")
    min_exclusive_area: Optional[float] = Field(None, description="최소 전용면적(제곱미터)")
    max_exclusive_area: Optional[float] = Field(None, description="최대 전용면적(제곱미터)")
    total_households: Optional[int] = Field(None, description="총 세대수")
    total_dong: Optional[int] = Field(None, description="총 동수")


class ApartmentResponse(ApartmentBase):
    """아파트 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Apartment Sale Transaction Schemas =====
class ApartmentSaleTransactionBase(BaseModel):
    """아파트 매매 거래 기본 스키마"""
    apartment_id: int = Field(..., description="아파트 ID")
    region_id: int = Field(..., description="지역 ID")
    deal_year: str = Field(..., max_length=4, description="거래년도")
    deal_month: str = Field(..., max_length=2, description="거래월")
    deal_day: str = Field(..., max_length=2, description="거래일")
    transaction_date: datetime = Field(..., description="거래일")
    deal_amount: int = Field(..., description="거래금액(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    dong: Optional[str] = Field(None, max_length=20, description="동")
    deal_type: Optional[str] = Field(None, max_length=20, description="거래유형")
    cancel_deal_day: Optional[str] = Field(None, max_length=8, description="해제사유발생일")
    dealing_gbn: Optional[str] = Field(None, max_length=20, description="거래구분")
    estate_agent_sgg_nm: Optional[str] = Field(None, max_length=50, description="중개사무소 소재지")
    seller_gbn: Optional[str] = Field(None, max_length=10, description="매도자 구분")
    buyer_gbn: Optional[str] = Field(None, max_length=10, description="매수자 구분")
    registration_date: Optional[str] = Field(None, max_length=8, description="등록일자")
    land_lease_gbn: Optional[str] = Field(None, max_length=10, description="토지임대부 여부")


class ApartmentSaleTransactionCreate(ApartmentSaleTransactionBase):
    """아파트 매매 거래 생성 스키마"""
    pass


class ApartmentSaleTransactionUpdate(BaseModel):
    """아파트 매매 거래 업데이트 스키마"""
    deal_amount: Optional[int] = Field(None, description="거래금액(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    dong: Optional[str] = Field(None, max_length=20, description="동")
    deal_type: Optional[str] = Field(None, max_length=20, description="거래유형")
    cancel_deal_day: Optional[str] = Field(None, max_length=8, description="해제사유발생일")
    dealing_gbn: Optional[str] = Field(None, max_length=20, description="거래구분")
    estate_agent_sgg_nm: Optional[str] = Field(None, max_length=50, description="중개사무소 소재지")
    seller_gbn: Optional[str] = Field(None, max_length=10, description="매도자 구분")
    buyer_gbn: Optional[str] = Field(None, max_length=10, description="매수자 구분")
    registration_date: Optional[str] = Field(None, max_length=8, description="등록일자")
    land_lease_gbn: Optional[str] = Field(None, max_length=10, description="토지임대부 여부")


class ApartmentSaleTransactionResponse(ApartmentSaleTransactionBase):
    """아파트 매매 거래 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Apartment Rent Transaction Schemas =====
class ApartmentRentTransactionBase(BaseModel):
    """아파트 전월세 거래 기본 스키마"""
    apartment_id: int = Field(..., description="아파트 ID")
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


class ApartmentRentTransactionCreate(ApartmentRentTransactionBase):
    """아파트 전월세 거래 생성 스키마"""
    pass


class ApartmentRentTransactionUpdate(BaseModel):
    """아파트 전월세 거래 업데이트 스키마"""
    deposit: Optional[int] = Field(None, description="보증금(만원)")
    monthly_rent: Optional[int] = Field(None, description="월세(만원)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(제곱미터)")
    floor: Optional[str] = Field(None, max_length=10, description="층수")
    contract_term: Optional[str] = Field(None, max_length=50, description="계약기간")
    contract_type: Optional[str] = Field(None, max_length=20, description="계약구분")
    use_rr_right: Optional[str] = Field(None, max_length=20, description="갱신요구권 사용여부")
    pre_deposit: Optional[int] = Field(None, description="종전 보증금(만원)")
    pre_monthly_rent: Optional[int] = Field(None, description="종전 월세(만원)")


class ApartmentRentTransactionResponse(ApartmentRentTransactionBase):
    """아파트 전월세 거래 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Combined Schemas =====
class ApartmentWithTransactions(ApartmentResponse):
    """거래 내역을 포함한 아파트 응답 스키마"""
    sale_transactions: list[ApartmentSaleTransactionResponse] = []
    rent_transactions: list[ApartmentRentTransactionResponse] = []

    class Config:
        from_attributes = True
