from sqlalchemy import(
    Integer,
    DECIMAL,
    Column,
    ForeignKey,
    TIMESTAMP
)
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
from sqlalchemy.sql import func 

class HouseSaleTransaction(Base):
    __tablename__ = "house_sale_transactions"
    id = Column(Integer, primary_key=True, index=True)
    sale_transaction_id = Column(Integer, ForeignKey("sale_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    total_floor_area = Column(DECIMAL(10, 2), comment="연면적")
    plottage_area = Column(DECIMAL(10, 2), comment="대지면적")

    create_at = Column(TIMESTAMP, server_default=func.now(), comment="생성일자")
    update_at = Column(TIMESTAMP, onupdate=func.now(), comment="수정일자")

    # Relationship
    sale_transaction = relationship("SaleTransaction", back_populates="house_sale_transactions")
    
    
