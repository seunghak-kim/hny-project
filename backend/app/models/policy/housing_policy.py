from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    TIMESTAMP,
    ForeignKey,
    Enum,
    UniqueConstraint,
    DECIMAL,
)
from sqlalchemy.sql import func 
from sqlalchemy.dialects.postgresql import JSONB
from app.db.postgre_db import Base
from sqlalchemy.orm import relationship
import enum

# EUM 클래스 정의 수정이 필요함
class PolicyStatus(enum.Enum): # 정책 상태에 대해서 Eunm 클래스 정의 
    RECRUITING = "recruiting"
    CLOSE = "close"
    ALWAYS = "always"
    SCHEDULED = "scheduled"    

class TargetType(enum.Enum):
    YOUTH = "youth"
    STUDENT = "student"
    JOB_SEEKER = "job_seeker"
    NEWLYWED = "newlywed"
    PROSPECTIVE_NEWLYWED = "prospective_newlywed"
    LOW_INCOM = "low_income"
    ELDERLY = "elderly"
    DISABLED = "disabled"
    SINGLE_PARENT = "single_parent"
    WELFARE_RECIPIENT = "welfare_recipient"
    
class IncomeCriteriaType(enum.Enum):
    MEDIAN = "median"
    URBAN_WORKER = "urban_worker"

class FinancialSupportType(enum.Enum):
    MONTHLY_RENT = "monthly_rent"
    INTEREST = "interest"
    GUARANTEE_FEE = "guarantee_fee"
    DEPOSIT_LOAN = "deposit_loan"

class LinkType(enum.Enum):
    APPLICATION = "application"
    INFO = "info"
    NOTICE = "notice"
    FAQ = "faq"
    RESOURCES = "resources"
    

# PolicyCategory 모델과 HousingPolicy 모델 정의   
class PolicyCategory(Base):
    __tablename__ = 'policy_categories'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String(100), nullable=False, unique=True, comment="정책 카테고리 이름")
    partent_id = Column(Integer, ForeignKey('policy_categories.id', ondelete='SET NULL'), comment="상위 카테고리 ID", index=True)
    level = Column(Integer, default=1, nullable=False, comment="카테고리 레벨", index=True)
    description = Column(Text, comment="카테고리 설명")
    is_active = Column(Boolean, default=True, nullable=False, comment="활성화 여부")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # 관계 설정
    parent = relationship("PolicyCategory", remote_side=[id], back_populates="children")
    children = relationship("PolicyCategory", back_populates="parent")
    housing_policies = relationship("HousingPolicy", back_populates="category")
    
class HousingPolicy(Base):
    __tablename__ = 'housing_policies'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    category_id = Column(Integer, ForeignKey('policy_categories.id', ondelete= 'CASCADE'), comment="정책 카테고리 ID", index=True)
    policy_name = Column(String(200), nullable=False)
    policy_code = Column(String(50), unique=True, index=True)
    summary = Column(Text, comment="정책 요약")
    description = Column(Text, comment="정책 상세 설명")
    application_method = Column(Text, comment="신청 방법")
    application_url = Column(String(500), comment="신청링크")
    officical_url = Column(String(500), comment="공식 안내페이지")
    housing_requirements = Column(JSONB, comment="주택 요건")                 
    lease_conditions = Column(JSONB, comment="임대 조건")
    required_documments = Column(JSONB, comment="필요 서류")
    regional_limitations = Column(JSONB, comment="지역별 지원한도")
    recruitment_info = Column(JSONB, comment="모집 정보")
    status = Column(Enum(PolicyStatus), default= PolicyStatus.ALWAYS, nullable=False, comment="정책 상태", index=True)
    is_active = Column(Boolean, default=True, nullable=False, comment="활성화 여부")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # 관계 설정
    category = relationship("PolicyCategory", back_populates="housing_policies")
    policy_target_types = relationship("PolicyTargetType", back_populates="policy", cascade="all, delete-orphan")
    eligibility_ranks = relationship("PolicyEligibilityRanks", back_populates="policy", cascade="all, delete-orphan")
    financial_supports = relationship("PolicyFinancialSupport", back_populates="policy", cascade="all, delete-orphan")
    contacts = relationship("PolicyContact", back_populates="policy", cascade="all, delete-orphan")
    links = relationship("PolicyLink", back_populates="policy", cascade="all, delete-orphan")
        
class PolicyTargetType(Base):
    __tablename__ = 'policy_target_types'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    policy_id = Column(Integer,ForeignKey('housing_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    target_type = Column(Enum(TargetType), nullable=False, index=True, comment="대상 유형")
    age_min = Column(Integer, comment="최소 연령")
    age_max = Column(Integer, comment="최대 연령")
    specific_conditions = Column(Text, comment="특정 조건")
    is_primary = Column(Boolean, default=False, nullable=False, comment="주 대상 여부")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    #관계 설정 
    policy = relationship("HousingPolicy", back_populates="policy_target_types")
    

class PolicyEligibilityRanks(Base):
    __tablename__ = 'policy_eligibility_ranks'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    policy_id = Column(Integer,ForeignKey('housing_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    target_type = Column(Integer, ForeignKey('policy_target_types.id', ondelete='CASCADE'), nullable=False)
    rank = Column(Integer, nullable=False, comment="순위 (1, 2, 3)")
    rank_name = Column(String(50), comment="순위 이름")
    target_description = Column(Text, comment="순위 대상 설명")
    income_criteria_percent = Column(Integer, comment="소득 기준 백분율")
    income_criteria_tyoe = Column(Enum(IncomeCriteriaType), comment="소득 기준 유형")
    asset_criteria = Column(DECIMAL(15, 2), comment="자산 기준")
    car_asset_criteria = Column(DECIMAL(15, 2), comment="자동차 자산 기준")
    additional_conditions = Column(JSONB, comment="추가 기준")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    policy = relationship("HousingPolicy", back_populates="eligibility_ranks")
    target_type_rel = relationship("PolicyTargetType")

    UniqueConstraint('policy_id', 'rank', name='idx_policy_eligibility_ranks_rank')
    
    
class PolicyFinancialSupport(Base):
    __tablename__ = 'policy_financial_supports'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    policy_id = Column(Integer,ForeignKey('housing_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    support_type = Column(Enum(FinancialSupportType), nullable=False, index=True, comment="지원 유형")
    max_amount = Column(DECIMAL(15, 2), comment="최대 지원 금액")
    monthly_support = Column(DECIMAL(15, 2), comment="월별 지원 금액")
    interest_rate = Column(DECIMAL(5, 2), comment="이자율")
    loan_limit_percent = Column(DECIMAL(5, 2), comment="대출 한도 비율")
    support_duration_months = Column(Integer, comment="지원 기간 (개월)")
    max_extension_years = Column(Integer, comment="최대 연장 기간 (년)")
    extension_conditions = Column(Text, comment="연장 조건")
    partner_banks = Column(JSONB, comment="제휴 은행 정보")
    lifetime_limit = Column(Integer, comment="생애 지원 횟수")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    policy = relationship("HousingPolicy", back_populates="financial_supports")


class PolicyContact(Base):
    __tablename__ = 'policy_contacts'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    policy_id = Column(Integer,ForeignKey('housing_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    contract_name = Column(String(100), nullable=False, comment="기관/부서명")
    phone_number = Column(String(50), comment="전화번호")
    is_primary = Column(Boolean, default=False, nullable=False, comment="주 연락처 여부")
    display_order = Column(Integer, default=0, nullable=False, comment="표시 순서")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    policy = relationship("HousingPolicy", back_populates="contacts")

class PolicyLink(Base):
    __tablename__ = 'policy_links'
    id = Column(Integer, primary_key=True, index=True, unique=True)
    policy_id = Column(Integer,ForeignKey('housing_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    link_type = Column(Enum(LinkType), nullable=False, index=True, comment="링크 유형")
    link_name = Column(String(200), nullable=False, comment="링크 이름")
    url = Column(String(500), nullable=False, comment="링크 URL")
    description = Column(Text, comment="링크 설명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    policy = relationship("HousingPolicy", back_populates="links")