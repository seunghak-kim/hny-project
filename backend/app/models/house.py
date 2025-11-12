"""
단독/다가구 관련 모델
공공데이터포털 API: RTMSDataSvcSHRent
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.models.base import RealEstateBase, SaleTransactionBase, RentTransactionBase


class House(RealEstateBase):
    """단독/다가구 기본 정보"""
    __tablename__ = "houses"

    # 건물 정보 참조
    building_id = Column(
        Integer,
        ForeignKey("buildings.id"),
        unique=True,
        nullable=True,
        index=True,
        comment="건물 ID (통합 건축물 정보)"
    )

    # 매물 정보
    property_code = Column(String(150), unique=True, nullable=False, index=True, comment="매물코드")
    name = Column(String(100), comment="건물명")
    house_type = Column(String(20), comment="주택유형(단독/다가구)")

    # Relationships
    building = relationship("Building", back_populates="house")
    sale_transactions = relationship(
        "HouseSaleTransaction",
        back_populates="house",
        cascade="all, delete-orphan"
    )
    rent_transactions = relationship(
        "HouseRentTransaction",
        back_populates="house",
        cascade="all, delete-orphan"
    )


class HouseSaleTransaction(SaleTransactionBase):
    """단독/다가구 매매 거래"""
    __tablename__ = "house_sale_transactions"

    # 단독/다가구 참조
    house_id = Column(
        Integer,
        ForeignKey("houses.id"),
        nullable=False,
        comment="단독/다가구 ID"
    )

    # 면적 정보
    total_floor_area = Column(Float, comment="연면적(제곱미터)")
    plottage_area = Column(Float, comment="대지권면적(제곱미터)")

    # Relationships
    house = relationship("House", back_populates="sale_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_house_sale_house_date', 'house_id', 'transaction_date'),
        Index('idx_house_sale_date', 'transaction_date'),
        Index('idx_house_sale_region_date', 'region_id', 'transaction_date'),
    )


class HouseRentTransaction(RentTransactionBase):
    """단독/다가구 전월세 거래"""
    __tablename__ = "house_rent_transactions"

    # 단독/다가구 참조
    house_id = Column(
        Integer,
        ForeignKey("houses.id"),
        nullable=False,
        comment="단독/다가구 ID"
    )

    # 면적 정보
    total_floor_area = Column(Float, comment="연면적(제곱미터)")

    # Relationships
    house = relationship("House", back_populates="rent_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_house_rent_house_date', 'house_id', 'transaction_date'),
        Index('idx_house_rent_date', 'transaction_date'),
        Index('idx_house_rent_region_date', 'region_id', 'transaction_date'),
    )
