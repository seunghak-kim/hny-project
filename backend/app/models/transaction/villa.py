from sqlalchemy import (
    Integer,
    Column,
    DECIMAL,
    ForeignKey,
    TIMESTAMP
)
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
from sqlalchemy.sql import func 

class VillaSaleTransaction(Base):
    __tablename__ = "villa_sale_transactions"
    id = Column(Integer, primary_key=True, index=True)
    sale_transaction_id = Column(Integer, ForeignKey("sale_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    land_area = Column(DECIMAL(10, 2), comment='대지권면적')

    create_at = Column(TIMESTAMP, server_default=func.now(), comment="생성일자")
    update_at = Column(TIMESTAMP, onupdate=func.now(), comment="수정일자")

    # Relationship
    sale_transaction = relationship("SaleTransaction", back_populates="villa_sale_transactions")
    