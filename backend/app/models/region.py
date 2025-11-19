# 부동산 가격정보 데이터
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
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
    RENT = "rent"  # 전/월세

class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    legal_dong_code = Column(String(20), unique=True, nullable=False, index=True, comment="법정동코드")
    cido_name = Column(String(20), nullable=False, comment="시도명")
    gu_name = Column(String(50), nullable=False, comment="지역명")
    umd_name = Column(String(50), nullable=False, comment="읍면동명")
    
    # 관리 정보
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationship
    buildings = relationship("Building", back_populates="region")
