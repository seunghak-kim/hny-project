"""
오피스텔 관련 모델
공공데이터 포털 API: RTMSDataSvcOffiTrade
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


class Officetel(RealEstateBase):
    """오피스텔 기본 정보"""
    __tablename__ = "officetels"

    # 건물 정보 참조
    building_id = Column(
        Integer,
        ForeignKey("buildings.id"),
        unique=True,
        nullable=True,
        index=True,
        comment="건물 ID (통합 건축물 정보)"
    )

    # 단지 정보
    complex_code = Column(String(150), unique=True, nullable=False, index=True, comment="단지코드")
    name = Column(String(100), nullable=False, comment="오피스텔명")
    sgg_name = Column(String(50), comment="시군구명")

    # Relationships
    building = relationship("Building", back_populates="officetel")
    sale_transactions = relationship(
        "OfficetelSaleTransaction",
        back_populates="officetel",
        cascade="all, delete-orphan"
    )
    rent_transactions = relationship(
        "OfficetelRentTransaction",
        back_populates="officetel",
        cascade="all, delete-orphan"
    )


class OfficetelSaleTransaction(SaleTransactionBase):
    """오피스텔 매매 거래"""
    __tablename__ = "officetel_sale_transactions"

    # 오피스텔 참조
    officetel_id = Column(
        Integer,
        ForeignKey("officetels.id"),
        nullable=False,
        comment="오피스텔 ID"
    )

    # 면적 및 위치
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    floor = Column(String(10), comment="층수")

    # Relationships
    officetel = relationship("Officetel", back_populates="sale_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_officetel_sale_officetel_date', 'officetel_id', 'transaction_date'),
        Index('idx_officetel_sale_date', 'transaction_date'),
        Index('idx_officetel_sale_region_date', 'region_id', 'transaction_date'),
    )


class OfficetelRentTransaction(RentTransactionBase):
    """오피스텔 전월세 거래"""
    __tablename__ = "officetel_rent_transactions"

    # 오피스텔 참조
    officetel_id = Column(
        Integer,
        ForeignKey("officetels.id"),
        nullable=False,
        comment="오피스텔 ID"
    )

    # 면적 및 위치
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    floor = Column(String(10), comment="층수")

    # Relationships
    officetel = relationship("Officetel", back_populates="rent_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_officetel_rent_officetel_date', 'officetel_id', 'transaction_date'),
        Index('idx_officetel_rent_date', 'transaction_date'),
        Index('idx_officetel_rent_region_date', 'region_id', 'transaction_date'),
    )
