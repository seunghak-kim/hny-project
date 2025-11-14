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
    total_households = Column(Integer, comment="총 세대수")

    # 지역 정보
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, comment="지역 ID")
    region_name = Column(String(50), comment="읍면동명")

    # 주소 정보
    address = Column(String(255), nullable=False, comment="지번 주소")
    road_address = Column(String(255), comment="도로명 주소")

    # 위치 정보 (좌표)
    latitude = Column(DECIMAL(10, 7), comment="위도")
    longitude = Column(DECIMAL(10, 7), comment="경도")

    # 주변 시설 정보 (JSON 형태)
    nearby_subway_stations = Column(Text, comment="1km 이내 지하철역 정보(JSON)")
    nearby_schools = Column(Text, comment="인근 초중고 정보(JSON)")
    nearby_marts = Column(Text, comment="인근 마트 정보(JSON)")

    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    region = relationship("Region")
    apartment = relationship("Apartment", back_populates="building", uselist=False)
    house = relationship("House", back_populates="building", uselist=False)
    villa = relationship("Villa", back_populates="building", uselist=False)
    officetel = relationship("Officetel", back_populates="building", uselist=False)

    # Indexes
    __table_args__ = (
        Index('idx_building_type', 'building_type'),
        Index('idx_building_region', 'region_id'),
        Index('idx_building_type_region', 'building_type', 'region_id'),
        Index('idx_building_coordinates', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f"<Building(id={self.id}, type={self.building_type.value}, name={self.name})>"
