"""건축물 통합 정보 모델"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    TIMESTAMP,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
from app.models.enums import PropertyType


class Building(Base):
    """건축물 기본 정보 (모든 부동산 타입의 공통 필드)"""
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)

    # 건물 타입
    building_type = Column(
        SQLEnum(PropertyType),
        nullable=False,
        index=True,
        comment="건물 유형 (아파트/오피스텔/단독/연립)"
    )

    # 건물 기본 정보
    name = Column(String(100), comment="건물명")
    build_year = Column(String(4), comment="건축년도")
    min_area = Column(DECIMAL(10, 2), comment="최소 전용면적")
    max_area = Column(DECIMAL(10, 2), comment="최대 전용면적")

    # 지역 정보
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="region ID")
    legal_dong = Column(String(100), comment="법정동명")
    # 주소 정보
    address = Column(String(255), nullable=False, comment="지번 주소")
    # road_address = Column(String(255), comment="도로명 주소")  # 현재 시스템에서는 사용되지 않음 

    # 위치 정보 (좌표)
    latitude = Column(DECIMAL(10, 7), comment="위도")
    longitude = Column(DECIMAL(10, 7), comment="경도")

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    region = relationship("Region", back_populates="buildings")
    infrastructures = relationship("Infrastructure", back_populates="building", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="building", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_building_type', 'building_type'),
        Index('idx_building_region', 'region_id'),
        Index('idx_building_type_region', 'building_type', 'region_id'),
        Index('idx_building_coordinates', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f"<Building(id={self.id}, type={self.building_type.value}, name={self.name})>"
