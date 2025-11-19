from sqlalchemy import(
    Integer,
    Column,
    Text,
    TIMESTAMP,
    ForeignKey
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base

class Infrastructure(Base):
    __tablename__ = "infrastructures"
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # 주변 시설 정보 (JSON 형태)
    nearby_subway_stations = Column(Text, comment="1km 이내 지하철역 정보(JSON)")
    nearby_schools = Column(Text, comment="인근 초중고 정보(JSON)")
    nearby_marts = Column(Text, comment="인근 마트 정보(JSON)")

    # 생성일자
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationship
    building = relationship("Building", back_populates="infrastructures")
    

