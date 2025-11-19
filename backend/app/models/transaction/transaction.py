from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    DECIMAL,
    ForeignKey,
    Enum
)
from app.db.postgre_db import Base 
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 
from app.models.enums import TransactionType

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"))
    transaction_type = Column(Enum(TransactionType), nullable= False, comment="거래 유형")
    exclusive_area = Column(DECIMAL(10, 2), nullable=False, comment="전용 면적")
    floor = Column(Integer, default=1, comment="거래 층")
    trans_date = Column(TIMESTAMP, comment="거래 일자")
    
    # 관리 정보 
    create_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일자")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일자")
    
    # Relationships
    building = relationship("Building", back_populates="transactions")
    sale_transactions = relationship("SaleTransaction", back_populates="transaction", cascade="all, delete-orphan")
    rent_transactions = relationship("RentTransaction", back_populates="transaction", cascade="all, delete-orphan")
    
    