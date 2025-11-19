"""은행 금융 상품 관련 모델"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    TIMESTAMP,
    ForeignKey,
    Table,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base


# Many-to-Many relationship table for content_chunks and keywords
chunk_keywords_association = Table(
    'chunk_keywords',
    Base.metadata,
    Column('chunk_id', Integer, ForeignKey('content_chunks.id', ondelete='CASCADE'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', TIMESTAMP(timezone=True), server_default=func.now())
)


class Bank(Base):
    """은행 마스터 테이블"""
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String(100), nullable=False, unique=True, comment="은행명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    products = relationship("BankProduct", back_populates="bank", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bank(id={self.id}, name='{self.bank_name}')>"


class ProductCategory(Base):
    """상품 카테고리 마스터 테이블"""
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False, unique=True, comment="카테고리명")
    description = Column(Text, comment="설명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    products = relationship("BankProduct", back_populates="product_category")

    def __repr__(self):
        return f"<ProductCategory(id={self.id}, name='{self.category_name}')>"


class BankProduct(Base):
    """금융 상품 정보 테이블"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(100), nullable=False, unique=True, comment="원본 상품 ID")
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, comment="은행 ID")
    product_category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False, comment="상품 카테고리 ID")
    product_name = Column(String(255), nullable=False, comment="상품명")
    summary = Column(Text, comment="상품 요약")
    source_document_url = Column(Text, comment="출처 URL")
    last_updated = Column(Date, comment="최종 업데이트 날짜")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    bank = relationship("Bank", back_populates="products")
    product_category = relationship("ProductCategory", back_populates="products")
    content_chunks = relationship("ContentChunk", back_populates="product", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_products_bank_id', 'bank_id'),
        Index('idx_products_category_id', 'product_category_id'),
        Index('idx_products_product_id', 'product_id'),
    )

    def __repr__(self):
        return f"<BankProduct(id={self.id}, product_id='{self.product_id}', name='{self.product_name}')>"


class ChunkCategory(Base):
    """청크 카테고리 마스터 테이블"""
    __tablename__ = "chunk_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False, unique=True, comment="카테고리명")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    content_chunks = relationship("ContentChunk", back_populates="chunk_category")

    def __repr__(self):
        return f"<ChunkCategory(id={self.id}, name='{self.category_name}')>"


class ContentChunk(Base):
    """상품 상세 정보 청크 테이블"""
    __tablename__ = "content_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String(100), nullable=False, unique=True, comment="원본 청크 ID")
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, comment="상품 ID")
    chunk_category_id = Column(Integer, ForeignKey("chunk_categories.id"), nullable=False, comment="청크 카테고리 ID")
    content_text = Column(Text, nullable=False, comment="상세 내용")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    product = relationship("BankProduct", back_populates="content_chunks")
    chunk_category = relationship("ChunkCategory", back_populates="content_chunks")
    keywords = relationship("Keyword", secondary=chunk_keywords_association, back_populates="content_chunks")

    # Indexes
    __table_args__ = (
        Index('idx_content_chunks_product_id', 'product_id'),
        Index('idx_content_chunks_category_id', 'chunk_category_id'),
    )

    def __repr__(self):
        return f"<ContentChunk(id={self.id}, chunk_id='{self.chunk_id}')>"


class Keyword(Base):
    """키워드 마스터 테이블"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, unique=True, comment="키워드")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    content_chunks = relationship("ContentChunk", secondary=chunk_keywords_association, back_populates="keywords")

    # Indexes
    __table_args__ = (
        Index('idx_keywords_keyword', 'keyword'),
    )

    def __repr__(self):
        return f"<Keyword(id={self.id}, keyword='{self.keyword}')>"
