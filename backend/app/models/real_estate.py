# 부동산 가격정보 데이터
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    Text,
    DECIMAL,
    Enum,
    TIMESTAMP,
    Index,
    ARRAY
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
import enum

# 부동산 종류
class PropertyType(enum.Enum):
    APARTMENT = "apartment"  # 아파트
    OFFICETEL = "officetel"  # 오피스텔
    ONEROOM = "oneroom"  # 원룸 (C01)
    VILLA = "villa"  # 빌라 (C02)
    HOUSE = "house"  # 단독/다가구 (C03)

# 거래 타입
class TransactionType(enum.Enum):
    SALE = "sale"  # 매매
    JEONSE = "jeonse"  # 전세
    RENT = "rent"  # 월세

class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True, comment="법정동코드")
    name = Column(String(50), nullable=False, comment="지역명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    real_estates = relationship("RealEstate", back_populates="region")
    transactions = relationship("Transaction", back_populates="region")
    
class RealEstate(Base):
    """부동산 기본 정보 (물리적 정보만 포함)"""
    __tablename__ = "real_estates"
    id = Column(Integer, primary_key=True, index=True)
    property_type = Column(Enum(PropertyType), nullable=False, comment="부동산 종류")
    code = Column(String(30), unique=True, nullable=False, index=True, comment="단지코드/매물코드")
    name = Column(String(100), nullable=False, comment="단지명/건물명")

    # 지역 정보
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="지역 ID")
    region = relationship("Region", back_populates="real_estates")

    # 주소 및 위치
    address = Column(String(255), nullable=False, comment="도로명주소")
    address_detail = Column(String(255), comment="상세주소")
    latitude = Column(DECIMAL(10, 7), comment="위도")
    longitude = Column(DECIMAL(10, 7), comment="경도")

    # 건물 기본 스펙
    total_households = Column(Integer, comment="총 세대수")
    total_buildings = Column(Integer, comment="총 동수")
    completion_date = Column(String(6), comment="준공년월(YYYYMM)")
    min_exclusive_area = Column(Float, comment="최소 전용면적(㎡)")
    max_exclusive_area = Column(Float, comment="최대 전용면적(㎡)")
    representative_area = Column(Float, comment="대표 전용면적(㎡)")
    floor_area_ratio = Column(Float, comment="용적률(%)")

    # 개별 매물 상세 정보 (단독/다가구/원룸/빌라용)
    exclusive_area = Column(Float, comment="전용면적 spc1(㎡)")
    supply_area = Column(Float, comment="공급면적 spc2(㎡)")
    exclusive_area_pyeong = Column(Float, comment="전용면적(평)")
    supply_area_pyeong = Column(Float, comment="공급면적(평)")
    direction = Column(String(20), comment="방향")
    floor_info = Column(String(50), comment="층 정보")

    # 건물 설명
    building_description = Column(Text, comment="건물 설명")
    tag_list = Column(ARRAY(String), comment="태그 리스트")

    # 매물 통계
    deal_count = Column(Integer, default=0, comment="매매 매물 수")
    lease_count = Column(Integer, default=0, comment="전세 매물 수")
    rent_count = Column(Integer, default=0, comment="월세 매물 수")
    short_term_rent_count = Column(Integer, default=0, comment="단기임대 매물 수")
    
    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    transactions = relationship("Transaction", back_populates="real_estate", cascade="all, delete-orphan")


class Transaction(Base):
    """실거래 내역"""
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)

    # 부동산 및 지역 정보
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"), nullable=False, comment="부동산 ID")
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="지역 ID")

    # 거래 기본 정보
    transaction_type = Column(Enum(TransactionType), comment="거래 유형")
    transaction_date = Column(TIMESTAMP(timezone=True), index=True, comment="거래일")

    # 가격 정보 - 개별 거래 단위
    sale_price = Column(Integer, default=0, comment="매매가(만원)")
    deposit = Column(Integer, default=0, comment="보증금(만원)")
    monthly_rent = Column(Integer, default=0, comment="월세(만원)")

    # 가격 범위 정보 - 단지/건물 단위 통계
    min_sale_price = Column(Integer, default=0, comment="최소 매매가(만원)")
    max_sale_price = Column(Integer, default=0, comment="최대 매매가(만원)")
    min_deposit = Column(Integer, default=0, comment="최소 보증금(만원)")
    max_deposit = Column(Integer, default=0, comment="최대 보증금(만원)")
    min_monthly_rent = Column(Integer, default=0, comment="최소 월세(만원)")
    max_monthly_rent = Column(Integer, default=0, comment="최대 월세(만원)")

    # 매물 번호 (CSV의 atclNo)
    article_no = Column(String(50), unique=True, index=True, comment="매물번호")
    article_confirm_ymd = Column(String(10), comment="매물확인일자")

    # 추후 사용될 필드명 

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")
    # Relationships
    real_estate = relationship("RealEstate", back_populates="transactions")
    region = relationship("Region", back_populates="transactions")

    # Indexes
    __table_args__ = (
        Index('idx_transaction_date_type', 'transaction_date', 'transaction_type'),
        Index('idx_real_estate_date', 'real_estate_id', 'transaction_date'),
    )
    
class NearbyFacility(Base):
    """ 주변 편의시설 """
    __tablename__ = "nearby_facilities"
    id = Column(Integer, primary_key=True, index=True)
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"), comment="부동산 ID")
    
    # 지하철 
    subway_line = Column(String(50), comment="지하철 노선")
    subway_distance = Column(Integer, comment="지하철 까지 거리")
    subway_walking_time = Column(Integer, comment="지하철 도보 시간")
    
    # 학교 
    elementary_schools = Column(Text, comment="초등학교")
    middle_schools = Column(Text, comment="중학교" )
    high_schools = Column(Text, comment="고등학교")
    
class RealEstateAgent(Base):
    """ 부동산 담당자 """
    __tablename__ = "real_estate_agents"
    id = Column(Integer, primary_key=True, index=True)
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"), comment="부동산 ID")

    # 중계정보
    agent_name = Column(String(100), comment="중개사명 (rltrNm)")
    company_name = Column(String(100), comment="메인 중개사명 (cpNm)")
    is_direct_trade = Column(Boolean, default=False, comment="직거래 유무 (directTradYn)")

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")
    