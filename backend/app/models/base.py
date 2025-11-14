"""부동산 모델의 공통 Base 클래스"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declared_attr
from app.db.postgre_db import Base


class RealEstateBase(Base):
    """부동산 기본 정보의 공통 필드

    Note: 주소, 좌표, 주변시설, 건축년도 등은 Building 테이블로 이동했습니다.
    각 부동산 모델은 building_id를 통해 Building과 연결됩니다.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)

    # 지역 정보
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="지역 ID")

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    @declared_attr
    def region(cls):
        return relationship("Region")


class TransactionBase(Base):
    """거래 정보의 공통 필드"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)

    # 지역 정보
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="지역 ID")

    # 거래 기본 정보
    deal_year = Column(String(4), nullable=False, comment="거래년도")
    deal_month = Column(String(2), nullable=False, comment="거래월")
    deal_day = Column(String(2), nullable=False, comment="거래일")
    transaction_date = Column(TIMESTAMP(timezone=True), index=True, comment="거래일")

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    @declared_attr
    def region(cls):
        return relationship("Region")


class SaleTransactionBase(TransactionBase):
    """매매 거래의 공통 필드"""
    __abstract__ = True

    # 거래 금액 (만원)
    deal_amount = Column(Integer, nullable=False, comment="거래금액(만원)")

    # 거래 상세 정보
    deal_type = Column(String(20), comment="거래유형")
    cancel_deal_day = Column(String(8), comment="해제사유발생일")
    dealing_gbn = Column(String(20), comment="거래구분")
    estate_agent_sgg_nm = Column(String(50), comment="중개사무소 소재지")
    seller_gbn = Column(String(10), comment="매도자 구분")
    buyer_gbn = Column(String(10), comment="매수자 구분")


class RentTransactionBase(TransactionBase):
    """전월세 거래의 공통 필드"""
    __abstract__ = True

    # 가격 정보
    deposit = Column(Integer, nullable=False, default=0, comment="보증금(만원)")
    monthly_rent = Column(Integer, default=0, comment="월세(만원)")

    # 계약 정보
    contract_term = Column(String(50), comment="계약기간")
    contract_type = Column(String(20), comment="계약구분")
    use_rr_right = Column(String(20), comment="갱신요구권 사용여부")
    pre_deposit = Column(Integer, comment="종전 보증금(만원)")
    pre_monthly_rent = Column(Integer, comment="종전 월세(만원)")
