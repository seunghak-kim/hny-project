from sqlalchemy import(
    Column,
    Integer,
    Text,
    ForeignKey,
    TIMESTAMP,
    Boolean,
    JSON,
)
from sqlalchemy.sql import func 
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base


class Law(Base):
    """
    법률 정보를 저장하는 모델
    """
    __tablename__ = "laws"

    law_id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(Text, nullable=False)  # 문서 유형
    title = Column(Text, nullable=False)  # 법률 제목
    number = Column(Text, nullable=False)  # 법률 번호
    enforcement_date = Column(Text, nullable=False)  # 시행일자
    category = Column(Text, nullable=False)  # 카테고리
    total_articles = Column(Integer, nullable=False)  # 총 조항 수
    last_article = Column(Text, nullable=False)  # 마지막 조항 번호
    source_file = Column(Text, nullable=False)  # 원문 파일 경로
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # 관계 설정
    articles = relationship("Article", back_populates="law", cascade="all, delete-orphan")

class Article(Base):
    """
    법률 조항 정보를 저장하는 모델
    """
    __tablename__ = "articles"

    article_id = Column(Integer, primary_key=True, index=True)
    law_id = Column(Integer, ForeignKey("laws.law_id", ondelete="CASCADE"), nullable=False, index=True)
    article_number = Column(Text, nullable=False)  # 조항 번호
    article_title = Column(Text, nullable=False)  # 조항 제목
    chapter = Column(Text, nullable=True)  # 장
    section = Column(Text, nullable= True)  # 절
    is_deleted = Column(Boolean, default=False, nullable=False)  # 삭제 여부
    is_tenant_protection = Column(Boolean, default=False, nullable=False)  # 임대차 보호법 여부
    is_tax_related = Column(Boolean, default=False, nullable=False)  # 세법 관련 여부
    is_delegation = Column(Boolean, default=False, nullable=False)  # 위임 여부
    is_penalty_related = Column(Boolean, default=False, nullable=False)  # 벌칙 관련 여부
    chunk_ids = Column(JSON, nullable=True)  # FAISS chunk ID 배열 (JSON) - FAISS 매칭용
    metadata_json = Column(JSON, nullable=True)  # 메타데이터 JSON
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # 관계 설정
    law = relationship("Law", back_populates="articles")

class LegalReference(Base):
    """
    법률 참조 정보를 저장하는 모델
    """
    __tablename__ = "legal_references"

    article_id = Column(Integer, ForeignKey("articles.article_id", ondelete="CASCADE"), primary_key=True)
    law_id = Column(Integer, ForeignKey("laws.law_id", ondelete="CASCADE"))
    article_number = Column(Text, nullable=False)  # 조항 번호
    article_title = Column(Text, nullable=False)  # 조항 제목
    chapter = Column(Text, nullable=True)  # 장
    section = Column(Text, nullable=True)  # 절
    is_deleted = Column(Boolean, default=False, nullable=False)  # 삭제 여부
    is_tenant_protection = Column(Boolean, default=False, nullable=False)  # 임대차 보호법 여부
    is_tax_related = Column(Boolean, default=False, nullable=False)  # 세법 관련 여부
    is_delegation = Column(Boolean, default=False, nullable=False)  # 위임 여부
    is_penalty_related = Column(Boolean, default=False, nullable=False)  # 벌칙 관련 여부
    chunk_ids = Column(JSON, nullable=True)  # FAISS chunk ID 배열 (JSON) - FAISS 매칭용
    metadata_json = Column(JSON, nullable=True)  # 메타데이터 JSON
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # 관계 설정
    law = relationship("Law")
    article = relationship("Article")