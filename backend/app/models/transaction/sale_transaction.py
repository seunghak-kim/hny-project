from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    DECIMAL,
    ForeignKey,
    BigInteger
)
from app.db.postgre_db import Base 
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 

class SaleTransaction(Base):
    __tablename__ = "sale_transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_amount = Column(BigInteger, comment="매매 금액")
    cdeal_type = Column(String(50), comment="거래 유형 ex: 직거래, 중개거래")
    cdeal_day = Column(String(50), comment="해제사유발생일 (거래 해제 시)")
    dealing_gbn = Column(String(50), comment="거래구분")
    estate_agent_sgg_nm = Column(String(200), comment="부동산중개소 시군구명")
    saler_gbn = Column(String(50), comment="판매구분")
    buyer_gbn = Column(String(50), comment="구매구분")
    
    # 관리 정보 
    create_at = Column(TIMESTAMP, server_default=func.now(), comment="생성일자")
    update_at = Column(TIMESTAMP, onupdate=func.now(), comment="수정일자")
    
    # Relationships
    transaction = relationship("Transaction", back_populates="sale_transactions")
    apartment_sale_transactions = relationship("ApartmentSaleTransaction", back_populates="sale_transaction", cascade="all, delete-orphan")
    villa_sale_transactions = relationship("VillaSaleTransaction", back_populates="sale_transaction", cascade="all, delete-orphan")
    house_sale_transactions = relationship("HouseSaleTransaction", back_populates="sale_transaction", cascade="all, delete-orphan")
    
    
    