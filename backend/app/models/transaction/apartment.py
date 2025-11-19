from sqlalchemy import (
    Integer,
    Column,
    DECIMAL,
    ForeignKey,
    TIMESTAMP,
    String
)
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
from sqlalchemy.sql import func 

class ApartmentSaleTransaction(Base):
    __tablename__ = "apartment_sale_transactions"
    id = Column(Integer, primary_key=True, index=True)
    sale_transaction_id = Column(Integer, ForeignKey("sale_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    apt_dong = Column(Integer, comment="아파트 동")
    land_leasehold_gbn = Column(String(20), comment="토지임대여부")
    rgst_date = Column(TIMESTAMP, comment="거래 등록일자")

    create_at = Column(TIMESTAMP, server_default=func.now(), comment="생성일자")
    update_at = Column(TIMESTAMP, onupdate=func.now(), comment="수정일자")

    # Relationship
    sale_transaction = relationship("SaleTransaction", back_populates="apartment_sale_transactions")
    