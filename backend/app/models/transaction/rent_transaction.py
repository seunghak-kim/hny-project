from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    DECIMAL,
    BigInteger,
    ForeignKey
)
from app.db.postgre_db import Base 
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 

class RentTransaction(Base):
    __tablename__  = "rent_transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    deposit = Column(BigInteger, comment="보증금")
    monthly_rent = Column(Integer, comment="월세")
    contract_term = Column(String(20), comment="계약기간")
    contract_type = Column(String(20), comment="계약유형")
    user_rr_right = Column(String(10), comment="재계약갱신권 사용여부")
    pre_deposit = Column(BigInteger, comment="이전보증금")
    pre_monthly_rent = Column(Integer, comment="이전월세")

    # 생성일자 
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="생성일자")
    updated_at = Column(TIMESTAMP, onupdate=func.now(), comment="수정일자")
    
    # Relationship
    transaction = relationship("Transaction", back_populates="rent_transactions")


    
    