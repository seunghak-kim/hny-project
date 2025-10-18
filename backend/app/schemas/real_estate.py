from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.models.real_estate import PropertyType, TransactionType


# ===== Region Schemas =====
class RegionBase(BaseModel):
    code: str = Field(..., max_length=20, description="법정동 코드")
    name: str = Field(..., max_length=50, description="지역명")


class RegionCreate(RegionBase):
    pass


class RegionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="지역명")


class RegionResponse(RegionBase):
    id: int = Field(..., description="지역명 ID")
    created_at: datetime = Field(..., description="생성일")
    updated_at: Optional[datetime] = Field(None, description="수정일")

    class Config:
        from_attributes = True


# ===== RealEstate Schemas =====
class RealEstateBase(BaseModel):
    property_type: PropertyType = Field(..., description="부동산 종류")
    code: str = Field(..., max_length=30, description="단지코드/매물코드")
    name: str = Field(..., max_length=100, description="단지명/건물명")
    region_id: int

    # 주소
    address: str = Field(..., max_length=255, description="도로명 주소")
    address_detail: Optional[str] = Field(None, max_length=255, description="상세주소")
    latitude: Optional[Decimal] = Field(None, description="위도")
    longitude: Optional[Decimal] = Field(None, description="경도")

    # 건물 기본스펙
    total_households: Optional[int] = Field(None, description="총 세대수")
    total_buildings: Optional[int] = Field(None, description="총 동수")
    completion_date: Optional[str] = Field(None, pattern=r'^\d{6}$', description="준공년월(YYYYMM)")
    min_exclusive_area: Optional[float] = Field(None, description="최소 전용면적(㎡)")
    max_exclusive_area: Optional[float] = Field(None, description="최대 전용면적(㎡)")
    representative_area: Optional[float] = Field(None, description="대표 전용면적(㎡)")
    floor_area_ratio: Optional[float] = Field(None, description="용적률(%)")

    # 개별 매물 상세 정보
    exclusive_area: Optional[float] = Field(None, description="전용면적(㎡)")
    supply_area: Optional[float] = Field(None, description="공급면적(㎡)")
    exclusive_area_pyeong: Optional[float] = Field(None, description="전용면적(평)")
    supply_area_pyeong: Optional[float] = Field(None, description="공급면적(평)")
    direction: Optional[str] = Field(None, max_length=20, description="방향")
    floor_info: Optional[str] = Field(None, max_length=50, description="층 정보")

    # 건물 설명
    building_description: Optional[str] = Field(None, description="건물 설명")
    tag_list: Optional[list[str]] = Field(None, description="태그 리스트")

    # 매물 통계
    deal_count: Optional[int] = Field(0, description="매매 매물 수")
    lease_count: Optional[int] = Field(0, description="전세 매물 수")
    rent_count: Optional[int] = Field(0, description="월세 매물 수")
    short_term_rent_count: Optional[int] = Field(0, description="단기임대 매물 수")

    @field_validator('completion_date')
    def validate_completion_date(cls, v):
        if v is not None:
            try:
                year = int(v[:4])
                month = int(v[4:6])
                if not (1900 <= year <= 2100 and 1 <= month <= 12):
                    raise ValueError
            except (ValueError, IndexError):
                raise ValueError('Invalid completion_date format. Must be YYYYMM')
        return v


class RealEstateCreate(RealEstateBase):
    pass


class RealEstateUpdate(BaseModel):
    property_type: Optional[PropertyType] = Field(None, description="부동산 종류")
    code: Optional[str] = Field(None, max_length=30, description="단지코드/매물코드")
    name: Optional[str] = Field(None, max_length=100, description="단지명/건물명")
    region_id: Optional[int] = None
    address: Optional[str] = Field(None, max_length=255, description="도로명 주소")
    address_detail: Optional[str] = Field(None, max_length=255, description="상세주소")
    latitude: Optional[Decimal] = Field(None, description="위도")
    longitude: Optional[Decimal] = Field(None, description="경도")
    total_households: Optional[int] = Field(None, description="총 세대수")
    total_buildings: Optional[int] = Field(None, description="총 동수")
    completion_date: Optional[str] = Field(None, pattern=r'^\d{6}$', description="준공년월(YYYYMM)")
    min_exclusive_area: Optional[float] = Field(None, description="최소 전용면적(㎡)")
    max_exclusive_area: Optional[float] = Field(None, description="최대 전용면적(㎡)")
    representative_area: Optional[float] = Field(None, description="대표 전용면적(㎡)")
    floor_area_ratio: Optional[float] = Field(None, description="용적률(%)")
    exclusive_area: Optional[float] = Field(None, description="전용면적(㎡)")
    supply_area: Optional[float] = Field(None, description="공급면적(㎡)")
    exclusive_area_pyeong: Optional[float] = Field(None, description="전용면적(평)")
    supply_area_pyeong: Optional[float] = Field(None, description="공급면적(평)")
    direction: Optional[str] = Field(None, max_length=20, description="방향")
    floor_info: Optional[str] = Field(None, max_length=50, description="층 정보")
    building_description: Optional[str] = Field(None, description="건물 설명")
    tag_list: Optional[list[str]] = Field(None, description="태그 리스트")
    deal_count: Optional[int] = Field(None, description="매매 매물 수")
    lease_count: Optional[int] = Field(None, description="전세 매물 수")
    rent_count: Optional[int] = Field(None, description="월세 매물 수")
    short_term_rent_count: Optional[int] = Field(None, description="단기임대 매물 수")


class RealEstateResponse(RealEstateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Transaction Schemas =====
class TransactionBase(BaseModel):
    real_estate_id: int
    region_id: int

    # 거래 기본 정보
    transaction_type: TransactionType = Field(..., description="거래 유형")
    transaction_date: datetime = Field(..., description="거래일")

    # 가격 정보 - 개별 거래 단위
    sale_price: Optional[int] = Field(0, ge=0, description="매매가(만원)")
    deposit: Optional[int] = Field(0, ge=0, description="보증금(만원)")
    monthly_rent: Optional[int] = Field(0, ge=0, description="월세(만원)")

    # 가격 범위 정보 - 단지/건물 단위 통계
    min_sale_price: Optional[int] = Field(0, ge=0, description="최소 매매가(만원)")
    max_sale_price: Optional[int] = Field(0, ge=0, description="최대 매매가(만원)")
    min_deposit: Optional[int] = Field(0, ge=0, description="최소 보증금(만원)")
    max_deposit: Optional[int] = Field(0, ge=0, description="최대 보증금(만원)")
    min_monthly_rent: Optional[int] = Field(0, ge=0, description="최소 월세(만원)")
    max_monthly_rent: Optional[int] = Field(0, ge=0, description="최대 월세(만원)")

    # 매물 번호
    article_no: Optional[str] = Field(None, max_length=50, description="매물번호")
    article_confirm_ymd: Optional[str] = Field(None, max_length=10, description="매물확인일자")


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = Field(None, description="거래 유형")
    transaction_date: Optional[datetime] = Field(None, description="거래일")
    sale_price: Optional[int] = Field(None, ge=0, description="매매가(만원)")
    deposit: Optional[int] = Field(None, ge=0, description="보증금(만원)")
    monthly_rent: Optional[int] = Field(None, ge=0, description="월세(만원)")
    min_sale_price: Optional[int] = Field(None, ge=0, description="최소 매매가(만원)")
    max_sale_price: Optional[int] = Field(None, ge=0, description="최대 매매가(만원)")
    min_deposit: Optional[int] = Field(None, ge=0, description="최소 보증금(만원)")
    max_deposit: Optional[int] = Field(None, ge=0, description="최대 보증금(만원)")
    min_monthly_rent: Optional[int] = Field(None, ge=0, description="최소 월세(만원)")
    max_monthly_rent: Optional[int] = Field(None, ge=0, description="최대 월세(만원)")
    article_no: Optional[str] = Field(None, max_length=50, description="매물번호")
    article_confirm_ymd: Optional[str] = Field(None, max_length=10, description="매물확인일자")


class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== Combined Schemas =====
class RealEstateWithTransactions(RealEstateResponse):
    transactions: list[TransactionResponse] = []

    class Config:
        from_attributes = True


class RealEstateWithRegion(RealEstateResponse):
    region: Optional[RegionResponse] = None

    class Config:
        from_attributes = True


class TransactionWithRealEstate(TransactionResponse):
    real_estate: Optional[RealEstateResponse] = None

    class Config:
        from_attributes = True
