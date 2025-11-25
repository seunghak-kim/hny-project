from sqlalchemy import (
    Column, 
    Integer,
    Text,
    TIMESTAMP,
    BLOB,
    UniqueConstraint,
    Index
)

from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, BYTEA
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.db.postgre_db import Base

class CheckPoint(Base):
    __tablename__ = "checkpoints"

    # 1. 대리키 도입 (깔끔한 관리 및 관계 설정을 위해)
    id = Column(Integer, primary_key=True, index=True)

    # 2. 비즈니스 로직상 식별자들 (PK에서 일반 컬럼으로 변경)
    # thread_id 등이 검색 조건으로 자주 쓰인다면 index=True 유지
    thread_id = Column(Text, nullable=False, index=True) 
    check_point_ns = Column(Text, nullable=False) # namespace
    check_point_ns_id = Column(Text, nullable=False)
    
    parent_checkpoint_id = Column(Text, nullable=True) # root는 없을 수 있으니 nullable?
    type = Column(Text, nullable=False) # type은 예약어일 수 있으나 Text라 무관, 찝찝하면 record_type 등으로 변경
    
    # 3. JSONB 변경 감지 적용
    check_point_data = Column(MutableDict.as_mutable(JSONB), nullable=False) # 이름 변경 제안: check_point -> check_point_data (클래스명과 혼동 방지)
    
    # 4. 예약어 충돌 방지 (metadata -> meta_data)
    meta_data = Column(MutableDict.as_mutable(JSONB), nullable=False, server_default='{}')

    __table_args__ = (
        # 5. 기존의 복합 PK 역할을 대신할 유니크 제약조건
        # 이 3개의 조합은 유일해야 한다.
        UniqueConstraint('thread_id', 'check_point_ns', 'check_point_ns_id', name='uq_checkpoint_identifier'),
        
        # (선택) parent_checkpoint_id 검색이 잦다면 인덱스 추가
        Index('ix_checkpoints_parent', 'parent_checkpoint_id'),
    )

class CheckPointBlob(Base):
    """체크포인트 블롭 모델"""
    __tablename__ = "checkpoint_blobs"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Text)
    check_point_ns = Column(Text)
    channel = Column(Text)
    version = Column(Text)
    type = Column(Text, nullable=False)
    blob = Column(BYTEA, nullable=False)

    # unique constraint to avoid duplicate blobs for the same checkpoint
    __table_args__ = (
        UniqueConstraint('thread_id', 'check_point_ns', 'channel', 'version', name='uq_checkpoint_blob'),
        )

class CheckPointWrite(Base):
    __tablename__ = "checkpoint_writes"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Text, nullable=False, index=True)
    check_point_ns = Column(Text, nullable=False)
    check_point_id = Column(Text, nullable=False)
    idx = Column(Integer, nullable=False)
    channel = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    value = Column(JSONB)
    
    __table_args__ = (
        UniqueConstraint('thread_id', 'check_point_ns', 'check_point_id', 'idx', 'channel', name='uq_checkpoint_write'),
    )