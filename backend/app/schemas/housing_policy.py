from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from backend.app.models.policy.housing_policy import (
    PolicyStatus,
    TargetType,
    IncomeCriteriaType,
    FinancialSupportType,
    LinkType
)


# ===== PolicyCategory Schemas =====
class PolicyCategoryBase(BaseModel):
    name: str = Field(..., max_length=100, description="정책 카테고리 이름")
    partent_id: Optional[int] = Field(None, description="상위 카테고리 ID")
    level: int = Field(1, ge=1, description="카테고리 레벨")
    description: Optional[str] = Field(None, description="카테고리 설명")
    is_active: bool = Field(True, description="활성화 여부")


class PolicyCategoryCreate(PolicyCategoryBase):
    pass


class PolicyCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    partent_id: Optional[int] = None
    level: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PolicyCategoryResponse(PolicyCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== PolicyTargetType Schemas =====
class PolicyTargetTypeBase(BaseModel):
    policy_id: int
    target_type: TargetType
    age_min: Optional[int] = Field(None, ge=0, description="최소 연령")
    age_max: Optional[int] = Field(None, ge=0, description="최대 연령")
    specific_conditions: Optional[str] = Field(None, description="특정 조건")
    is_primary: bool = Field(False, description="주 대상 여부")


class PolicyTargetTypeCreate(PolicyTargetTypeBase):
    pass


class PolicyTargetTypeUpdate(BaseModel):
    target_type: Optional[TargetType] = None
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    specific_conditions: Optional[str] = None
    is_primary: Optional[bool] = None


class PolicyTargetTypeResponse(PolicyTargetTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== PolicyEligibilityRanks Schemas =====
class PolicyEligibilityRanksBase(BaseModel):
    policy_id: int
    target_type: int
    rank: int = Field(..., ge=1, description="순위")
    rank_name: Optional[str] = Field(None, max_length=50, description="순위 이름")
    target_description: Optional[str] = Field(None, description="순위 대상 설명")
    income_criteria_percent: Optional[int] = Field(None, ge=0, description="소득 기준 백분율")
    income_criteria_type: Optional[IncomeCriteriaType] = None
    asset_criteria: Optional[Decimal] = Field(None, description="자산 기준")
    car_asset_criteria: Optional[Decimal] = Field(None, description="자동차 자산 기준")
    additional_conditions: Optional[Dict[str, Any]] = Field(None, description="추가 기준")


class PolicyEligibilityRanksCreate(PolicyEligibilityRanksBase):
    pass


class PolicyEligibilityRanksUpdate(BaseModel):
    target_type: Optional[int] = None
    rank: Optional[int] = Field(None, ge=1)
    rank_name: Optional[str] = Field(None, max_length=50)
    target_description: Optional[str] = None
    income_criteria_percent: Optional[int] = Field(None, ge=0)
    income_criteria_type: Optional[IncomeCriteriaType] = None
    asset_criteria: Optional[Decimal] = None
    car_asset_criteria: Optional[Decimal] = None
    additional_conditions: Optional[Dict[str, Any]] = None


class PolicyEligibilityRanksResponse(PolicyEligibilityRanksBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== PolicyFinancialSupport Schemas =====
class PolicyFinancialSupportBase(BaseModel):
    policy_id: int
    support_type: FinancialSupportType
    max_amount: Optional[Decimal] = Field(None, description="최대 지원 금액")
    monthly_support: Optional[Decimal] = Field(None, description="월별 지원 금액")
    interest_rate: Optional[Decimal] = Field(None, ge=0, description="이자율")
    loan_limit_percent: Optional[Decimal] = Field(None, ge=0, description="대출 한도 비율")
    support_duration_months: Optional[int] = Field(None, ge=0, description="지원 기간 (개월)")
    max_extension_years: Optional[int] = Field(None, ge=0, description="최대 연장 기간 (년)")
    extension_conditions: Optional[str] = Field(None, description="연장 조건")
    partner_banks: Optional[List[Dict[str, Any]]] = Field(None, description="제휴 은행 정보")
    lifetime_limit: Optional[int] = Field(None, ge=0, description="생애 지원 횟수")


class PolicyFinancialSupportCreate(PolicyFinancialSupportBase):
    pass


class PolicyFinancialSupportUpdate(BaseModel):
    support_type: Optional[FinancialSupportType] = None
    max_amount: Optional[Decimal] = None
    monthly_support: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = Field(None, ge=0)
    loan_limit_percent: Optional[Decimal] = Field(None, ge=0)
    support_duration_months: Optional[int] = Field(None, ge=0)
    max_extension_years: Optional[int] = Field(None, ge=0)
    extension_conditions: Optional[str] = None
    partner_banks: Optional[List[Dict[str, Any]]] = None
    lifetime_limit: Optional[int] = Field(None, ge=0)


class PolicyFinancialSupportResponse(PolicyFinancialSupportBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== PolicyContact Schemas =====
class PolicyContactBase(BaseModel):
    policy_id: int
    contract_name: str = Field(..., max_length=100, description="기관/부서명")
    phone_number: Optional[str] = Field(None, max_length=50, description="전화번호")
    is_primary: bool = Field(False, description="주 연락처 여부")
    display_order: int = Field(0, ge=0, description="표시 순서")


class PolicyContactCreate(PolicyContactBase):
    pass


class PolicyContactUpdate(BaseModel):
    contract_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)


class PolicyContactResponse(PolicyContactBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== PolicyLink Schemas =====
class PolicyLinkBase(BaseModel):
    policy_id: int
    link_type: LinkType
    link_name: str = Field(..., max_length=200, description="링크 이름")
    url: str = Field(..., max_length=500, description="링크 URL")
    description: Optional[str] = Field(None, description="링크 설명")


class PolicyLinkCreate(PolicyLinkBase):
    pass


class PolicyLinkUpdate(BaseModel):
    link_type: Optional[LinkType] = None
    link_name: Optional[str] = Field(None, max_length=200)
    url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None


class PolicyLinkResponse(PolicyLinkBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== HousingPolicy Schemas =====
class HousingPolicyBase(BaseModel):
    category_id: int
    policy_name: str = Field(..., max_length=200, description="정책명")
    policy_code: Optional[str] = Field(None, max_length=50, description="정책 코드")
    summary: Optional[str] = Field(None, description="정책 요약")
    description: Optional[str] = Field(None, description="정책 상세 설명")
    application_method: Optional[str] = Field(None, description="신청 방법")
    application_url: Optional[str] = Field(None, max_length=500, description="신청링크")
    officical_url: Optional[str] = Field(None, max_length=500, description="공식 안내페이지")
    housing_requirements: Optional[Dict[str, Any]] = Field(None, description="주택 요건")
    lease_conditions: Optional[Dict[str, Any]] = Field(None, description="임대 조건")
    required_documments: Optional[List[str]] = Field(None, description="필요 서류")
    regional_limitations: Optional[Dict[str, Any]] = Field(None, description="지역별 지원한도")
    recruitment_info: Optional[Dict[str, Any]] = Field(None, description="모집 정보")
    status: PolicyStatus = Field(PolicyStatus.ALWAYS, description="정책 상태")
    is_active: bool = Field(True, description="활성화 여부")


class HousingPolicyCreate(HousingPolicyBase):
    pass


class HousingPolicyUpdate(BaseModel):
    category_id: Optional[int] = None
    policy_name: Optional[str] = Field(None, max_length=200)
    policy_code: Optional[str] = Field(None, max_length=50)
    summary: Optional[str] = None
    description: Optional[str] = None
    application_method: Optional[str] = None
    application_url: Optional[str] = Field(None, max_length=500)
    officical_url: Optional[str] = Field(None, max_length=500)
    housing_requirements: Optional[Dict[str, Any]] = None
    lease_conditions: Optional[Dict[str, Any]] = None
    required_documments: Optional[List[str]] = None
    regional_limitations: Optional[Dict[str, Any]] = None
    recruitment_info: Optional[Dict[str, Any]] = None
    status: Optional[PolicyStatus] = None
    is_active: Optional[bool] = None


class HousingPolicyResponse(HousingPolicyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== HousingPolicy with Related Data =====
class HousingPolicyWithDetails(HousingPolicyResponse):
    """모든 관련 데이터를 포함한 상세 정책 정보"""
    category: Optional[PolicyCategoryResponse] = None
    policy_target_types: List[PolicyTargetTypeResponse] = []
    eligibility_ranks: List[PolicyEligibilityRanksResponse] = []
    financial_supports: List[PolicyFinancialSupportResponse] = []
    contacts: List[PolicyContactResponse] = []
    links: List[PolicyLinkResponse] = []

    class Config:
        from_attributes = True


# ===== PolicyCategory with Children =====
class PolicyCategoryWithChildren(PolicyCategoryResponse):
    """하위 카테고리를 포함한 카테고리"""
    children: List['PolicyCategoryWithChildren'] = []
    housing_policies: List[HousingPolicyResponse] = []

    class Config:
        from_attributes = True


# Update forward references for recursive model
PolicyCategoryWithChildren.model_rebuild()
