"""은행 금융 상품 관련 Pydantic 스키마"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date


# ==================== Bank Schemas ====================

class BankBase(BaseModel):
    """은행 기본 스키마"""
    bank_name: str = Field(..., min_length=1, max_length=100, description="은행명")


class BankCreate(BankBase):
    """은행 생성 스키마"""
    pass


class BankUpdate(BaseModel):
    """은행 수정 스키마"""
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100, description="은행명")


class BankResponse(BankBase):
    """은행 응답 스키마"""
    id: int = Field(..., description="은행 ID")
    created_at: datetime = Field(..., description="생성일")
    updated_at: Optional[datetime] = Field(None, description="수정일")

    model_config = ConfigDict(from_attributes=True)


# ==================== Product Category Schemas ====================

class ProductCategoryBase(BaseModel):
    """상품 카테고리 기본 스키마"""
    category_name: str = Field(..., min_length=1, max_length=100, description="카테고리명")
    description: Optional[str] = Field(None, description="설명")


class ProductCategoryCreate(ProductCategoryBase):
    """상품 카테고리 생성 스키마"""
    pass


class ProductCategoryUpdate(BaseModel):
    """상품 카테고리 수정 스키마"""
    category_name: Optional[str] = Field(None, min_length=1, max_length=100, description="카테고리명")
    description: Optional[str] = Field(None, description="설명")


class ProductCategoryResponse(ProductCategoryBase):
    """상품 카테고리 응답 스키마"""
    id: int = Field(..., description="카테고리 ID")
    created_at: datetime = Field(..., description="생성일")

    model_config = ConfigDict(from_attributes=True)


# ==================== Chunk Category Schemas ====================

class ChunkCategoryBase(BaseModel):
    """청크 카테고리 기본 스키마"""
    category_name: str = Field(..., min_length=1, max_length=100, description="카테고리명")


class ChunkCategoryCreate(ChunkCategoryBase):
    """청크 카테고리 생성 스키마"""
    pass


class ChunkCategoryResponse(ChunkCategoryBase):
    """청크 카테고리 응답 스키마"""
    id: int = Field(..., description="카테고리 ID")
    created_at: datetime = Field(..., description="생성일")

    model_config = ConfigDict(from_attributes=True)


# ==================== Keyword Schemas ====================

class KeywordBase(BaseModel):
    """키워드 기본 스키마"""
    keyword: str = Field(..., min_length=1, max_length=255, description="키워드")


class KeywordCreate(KeywordBase):
    """키워드 생성 스키마"""
    pass


class KeywordResponse(KeywordBase):
    """키워드 응답 스키마"""
    id: int = Field(..., description="키워드 ID")
    created_at: datetime = Field(..., description="생성일")

    model_config = ConfigDict(from_attributes=True)


# ==================== Content Chunk Schemas ====================

class ContentChunkBase(BaseModel):
    """상품 상세 정보 청크 기본 스키마"""
    chunk_id: str = Field(..., min_length=1, max_length=100, description="청크 ID")
    content_text: str = Field(..., min_length=1, description="상세 내용")


class ContentChunkCreate(ContentChunkBase):
    """상품 상세 정보 청크 생성 스키마"""
    product_id: int = Field(..., description="상품 ID")
    chunk_category_id: int = Field(..., description="청크 카테고리 ID")
    keyword_ids: Optional[List[int]] = Field(default=[], description="키워드 ID 목록")


class ContentChunkUpdate(BaseModel):
    """상품 상세 정보 청크 수정 스키마"""
    content_text: Optional[str] = Field(None, min_length=1, description="상세 내용")
    chunk_category_id: Optional[int] = Field(None, description="청크 카테고리 ID")
    keyword_ids: Optional[List[int]] = Field(None, description="키워드 ID 목록")


class ContentChunkResponse(ContentChunkBase):
    """상품 상세 정보 청크 응답 스키마"""
    id: int = Field(..., description="청크 ID")
    product_id: int = Field(..., description="상품 ID")
    chunk_category_id: int = Field(..., description="청크 카테고리 ID")
    created_at: datetime = Field(..., description="생성일")

    # Nested objects
    chunk_category: Optional[ChunkCategoryResponse] = None
    keywords: List[KeywordResponse] = Field(default=[], description="키워드 목록")

    model_config = ConfigDict(from_attributes=True)


# ==================== Bank Product Schemas ====================

class BankProductBase(BaseModel):
    """금융 상품 기본 스키마"""
    product_id: str = Field(..., min_length=1, max_length=100, description="상품 ID")
    product_name: str = Field(..., min_length=1, max_length=255, description="상품명")
    summary: Optional[str] = Field(None, description="상품 요약")
    source_document_url: Optional[str] = Field(None, description="출처 URL")
    last_updated: Optional[date] = Field(None, description="최종 업데이트 날짜")


class BankProductCreate(BankProductBase):
    """금융 상품 생성 스키마"""
    bank_id: int = Field(..., description="은행 ID")
    product_category_id: int = Field(..., description="상품 카테고리 ID")


class BankProductUpdate(BaseModel):
    """금융 상품 수정 스키마"""
    product_name: Optional[str] = Field(None, min_length=1, max_length=255, description="상품명")
    summary: Optional[str] = Field(None, description="상품 요약")
    source_document_url: Optional[str] = Field(None, description="출처 URL")
    last_updated: Optional[date] = Field(None, description="최종 업데이트 날짜")
    bank_id: Optional[int] = Field(None, description="은행 ID")
    product_category_id: Optional[int] = Field(None, description="상품 카테고리 ID")


class BankProductResponse(BankProductBase):
    """금융 상품 응답 스키마"""
    id: int = Field(..., description="상품 ID")
    bank_id: int = Field(..., description="은행 ID")
    product_category_id: int = Field(..., description="상품 카테고리 ID")
    created_at: datetime = Field(..., description="생성일")
    updated_at: Optional[datetime] = Field(None, description="수정일")

    # Nested objects
    bank: Optional[BankResponse] = None
    product_category: Optional[ProductCategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BankProductDetailResponse(BankProductResponse):
    """금융 상품 상세 응답 스키마 (청크 포함)"""
    content_chunks: List[ContentChunkResponse] = Field(default=[], description="상세 정보 청크 목록")

    model_config = ConfigDict(from_attributes=True)


# ==================== Search Schemas ====================

class BankProductSearchRequest(BaseModel):
    """금융 상품 검색 요청 스키마"""
    query: Optional[str] = Field(None, description="검색 쿼리")
    bank_name: Optional[str] = Field(None, description="은행명")
    product_category: Optional[str] = Field(None, description="상품 카테고리")
    keywords: Optional[List[str]] = Field(default=[], description="키워드 목록")
    limit: int = Field(default=10, ge=1, le=100, description="결과 제한")
    offset: int = Field(default=0, ge=0, description="결과 오프셋")


class BankProductSearchResponse(BaseModel):
    """금융 상품 검색 응답 스키마"""
    total: int = Field(..., description="총 결과 수")
    items: List[BankProductResponse] = Field(..., description="상품 목록")
    limit: int = Field(..., description="결과 제한")
    offset: int = Field(..., description="결과 오프셋")

    model_config = ConfigDict(from_attributes=True)


# ==================== Statistics Schemas ====================

class BankStatistics(BaseModel):
    """은행별 통계 스키마"""
    bank_name: str = Field(..., description="은행명")
    total_products: int = Field(..., description="총 상품 수")
    product_categories: List[dict] = Field(..., description="카테고리별 상품 수")

    model_config = ConfigDict(from_attributes=True)


class CategoryStatistics(BaseModel):
    """카테고리별 통계 스키마"""
    category_name: str = Field(..., description="카테고리명")
    total_products: int = Field(..., description="총 상품 수")
    banks: List[dict] = Field(..., description="은행별 상품 수")

    model_config = ConfigDict(from_attributes=True)
