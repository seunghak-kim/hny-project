from sqlalchemy import Integer, String, Float, DECIMAL, Text, TIMESTAMP, ForeignKey, Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base

class TrustScore(Base):
    """건물 신뢰도 점수 (Building 기반)"""
    __tablename__ = "trust_scores"
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False, index=True, comment="건물 ID")
    score = Column(DECIMAL(5, 2), nullable=False, comment="신뢰점수 (0-100)")
    verification_notes = Column(Text, comment="검증 내용")
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="계산일자")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    building = relationship("Building")