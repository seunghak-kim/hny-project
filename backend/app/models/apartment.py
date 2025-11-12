"""아파트 관련 모델"""
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


class Apartment(RealEstateBase):
    """아파트 기본 정보"""
    __tablename__ = "apartments"

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
    name = Column(String(100), nullable=False, comment="아파트 단지명")

    # 면적 정보
    min_exclusive_area = Column(Float, comment="최소 전용면적(제곱미터)")
    max_exclusive_area = Column(Float, comment="최대 전용면적(제곱미터)")

    # 단지 스펙
    total_households = Column(Integer, comment="총 세대수")
    total_dong = Column(Integer, comment="총 동수")

    # Relationships
    building = relationship("Building", back_populates="apartment")
    sale_transactions = relationship(
        "ApartmentSaleTransaction",
        back_populates="apartment",
        cascade="all, delete-orphan"
    )
    rent_transactions = relationship(
        "ApartmentRentTransaction",
        back_populates="apartment",
        cascade="all, delete-orphan"
    )


class ApartmentSaleTransaction(SaleTransactionBase):
    """아파트 매매 거래"""
    __tablename__ = "apartment_sale_transactions"

    # 아파트 참조
    apartment_id = Column(
        Integer,
        ForeignKey("apartments.id"),
        nullable=False,
        comment="아파트 ID"
    )

    # 면적 및 위치
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    floor = Column(String(10), comment="층수")
    dong = Column(String(20), comment="동")

    # 추가 정보
    registration_date = Column(String(8), comment="등록일자")
    land_lease_gbn = Column(String(10), comment="토지임대부 여부")

    # Relationships
    apartment = relationship("Apartment", back_populates="sale_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_apt_sale_apartment_date', 'apartment_id', 'transaction_date'),
        Index('idx_apt_sale_date', 'transaction_date'),
        Index('idx_apt_sale_region_date', 'region_id', 'transaction_date'),
    )


class ApartmentRentTransaction(RentTransactionBase):
    """아파트 전월세 거래"""
    __tablename__ = "apartment_rent_transactions"

    # 아파트 참조
    apartment_id = Column(
        Integer,
        ForeignKey("apartments.id"),
        nullable=False,
        comment="아파트 ID"
    )

    # 면적 및 위치
    exclusive_area = Column(Float, comment="전용면적(제곱미터)")
    floor = Column(String(10), comment="층수")

    # Relationships
    apartment = relationship("Apartment", back_populates="rent_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_apt_rent_apartment_date', 'apartment_id', 'transaction_date'),
        Index('idx_apt_rent_date', 'transaction_date'),
        Index('idx_apt_rent_region_date', 'region_id', 'transaction_date'),
    )
