"""
연립/다세대 관련 모델
공공데이터 포털 API명 RTMSDataSvcRHTrade
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


class Villa(RealEstateBase):
    """연립/다세대 기본 정보"""
    __tablename__ = "villas"

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
    name = Column(String(100), nullable=False, comment="주택명")

    # Relationships
    building = relationship("Building", back_populates="villa")
    sale_transactions = relationship(
        "VillaSaleTransaction",
        back_populates="villa",
        cascade="all, delete-orphan"
    )
    rent_transactions = relationship(
        "VillaRentTransaction",
        back_populates="villa",
        cascade="all, delete-orphan"
    )


class VillaSaleTransaction(SaleTransactionBase):
    """연립/다세대 매매 거래"""
    __tablename__ = "villa_sale_transactions"

    # 연립/다세대 참조
    villa_id = Column(
        Integer,
        ForeignKey("villas.id"),
        nullable=False,
        comment="연립/다세대 ID"
    )

    # 면적 정보
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    land_area = Column(Float, comment="대지권면적(제곱미터)")
    floor = Column(String(10), comment="층수")

    # 추가 정보
    registration_date = Column(String(8), comment="등록일자")

    # Relationships
    villa = relationship("Villa", back_populates="sale_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_villa_sale_villa_date', 'villa_id', 'transaction_date'),
        Index('idx_villa_sale_date', 'transaction_date'),
        Index('idx_villa_sale_region_date', 'region_id', 'transaction_date'),
    )


class VillaRentTransaction(RentTransactionBase):
    """연립/다세대 전월세 거래"""
    __tablename__ = "villa_rent_transactions"

    # 연립/다세대 참조
    villa_id = Column(
        Integer,
        ForeignKey("villas.id"),
        nullable=False,
        comment="연립/다세대 ID"
    )

    # 면적 및 위치
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    floor = Column(String(10), comment="층수")

    # Relationships
    villa = relationship("Villa", back_populates="rent_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_villa_rent_villa_date', 'villa_id', 'transaction_date'),
        Index('idx_villa_rent_date', 'transaction_date'),
        Index('idx_villa_rent_region_date', 'region_id', 'transaction_date'),
    )
