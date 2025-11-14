from sqlalchemy import(
    Column,
    Integer,
    String,
    TIMESTAMP,
    ForeignKey,
    Index,
    Text,
    JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base

class Law(Base):
    """법률 모델 """
    __tablename__ = "laws"
    law_id = Column(Integer, primary_key=True, index=True, comment="법률 ID")
    doc_type = Column(String(20), nullable=False, comment="법률/시행령/시행규칙/대법원규칙/용어집/기타")
    title = Column(String(255), nullable=False, comment="법령명")
    number = Column(String(20), comment="법령번호")
    enforcement_date = Column(String(20), comment="시행일")
    category = Column(String(50), nullable=False, comment="카테고리")
    total_articles = Column(Integer, default=0, comment="총 조항 수")
    last_article = Column(String(20), comment="마지막 조항 번호")
    source_file = Column(Text, comment="원본 파일명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성된 시간")

    # Relationships
    articles = relationship("Article", back_populates="law", cascade="all, delete-orphan")

    # Indexes and Constraints
    __table_args__ = (
        UniqueConstraint('title', 'number', 'doc_type', name='uq_law_title_number_type'),
        Index('idx_laws_doc_type', 'doc_type'),
        Index('idx_laws_title', 'title'),
        Index('idx_laws_category', 'category'),
        Index('idx_laws_enforcement_date', 'enforcement_date'),
    )
class Article(Base):
    """조항 상세 정보 """
    __tablename__ = "articles"
    article_id = Column(Integer, primary_key=True, index=True, comment="조항 ID")
    law_id = Column(Integer, ForeignKey("laws.law_id", ondelete="CASCADE"), nullable=False, comment="법률 ID")
    article_number = Column(String(20), nullable=False, comment="조항 번호(예: 제1조)")
    article_title = Column(String(255), comment="조항 제목")
    chapter = Column(String(50), comment="장")
    section = Column(String(50), comment="절")
    is_deleted = Column(Integer, default=0, comment="삭제 여부 (0: 유효, 1: 삭제)")
    is_tenant_protection = Column(Integer, default=0, comment="임차인 보호 조항")
    is_tax_related = Column(Integer, default=0, comment="세금 관련")
    is_delegation = Column(Integer, default=0, comment="위임")
    is_penalty_related = Column(Integer, default=0, comment="벌칙")
    chunk_ids = Column(Text, comment="ChromaDB chunk ID 배열(JSON)")
    metadata_json = Column(JSON, comment="전체 메타데이터 (JSON)")

    # Relationships
    law = relationship("Law", back_populates="articles")
    references = relationship("LegalReference", back_populates="article", cascade="all, delete-orphan")

    # Indexes (UNIQUE 제약조건 제거 - 같은 article_number가 여러 번 나올 수 있음)
    __table_args__ = (
        Index('idx_articles_law_id', 'law_id'),
        Index('idx_articles_number', 'article_number'),
        Index('idx_articles_deleted', 'is_deleted'),
        Index('idx_articles_tenant', 'is_tenant_protection'),
        Index('idx_articles_tax', 'is_tax_related'),
        Index('idx_articles_delegation', 'is_delegation'),
        Index('idx_articles_penalty', 'is_penalty_related'),
    )


class LegalReference(Base):
    """법률 참조 관계 """
    __tablename__ = "legal_references"
    reference_id = Column(Integer, primary_key=True, index=True, comment="참조 ID")
    source_article_id = Column(Integer, ForeignKey("articles.article_id", ondelete="CASCADE"), nullable=False, comment="원본 조항 ID")
    reference_type = Column(String(50), nullable=False, comment="law_references, decree_references, form_references")
    target_law_title = Column(String(255), comment="참조 대상 법령명")
    target_article_number = Column(String(20), comment="참조 대상 조항")
    reference_text = Column(Text, comment="원본 참조 텍스트")

    # Relationships
    article = relationship("Article", back_populates="references")

    # Indexes
    __table_args__ = (
        Index('idx_references_source', 'source_article_id'),
        Index('idx_references_type', 'reference_type'),
    )