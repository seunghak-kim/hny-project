from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any


# ==================== LegalReference Schemas ====================

class LegalReferenceBase(BaseModel):
    """법률 참조 기본 스키마"""
    reference_type: Optional[str] = Field(None, max_length=50, description="law_references, decree_references, form_references")
    target_law_title: Optional[str] = Field(None, max_length=100, description="참조 대상 법령명")
    target_article_number: Optional[str] = Field(None, max_length=20, description="참조 대상 조항")
    reference_text: Optional[str] = Field(None, description="참조 내용")


class LegalReferenceCreate(LegalReferenceBase):
    """법률 참조 생성 스키마"""
    source_article_id: int = Field(..., description="원본 조항 ID")


class LegalReferenceUpdate(BaseModel):
    """법률 참조 수정 스키마"""
    reference_type: Optional[str] = Field(None, max_length=50)
    target_law_title: Optional[str] = Field(None, max_length=100)
    target_article_number: Optional[str] = Field(None, max_length=20)
    reference_text: Optional[str] = None


class LegalReferenceResponse(LegalReferenceBase):
    """법률 참조 응답 스키마"""
    reference_id: int
    source_article_id: int

    model_config = ConfigDict(from_attributes=True)


# ==================== Article Schemas ====================

class ArticleBase(BaseModel):
    """조항 기본 스키마"""
    article_number: str = Field(..., max_length=20, description="조항 번호(예: 제1조)")
    article_title: Optional[str] = Field(None, max_length=255, description="조항 제목")
    chapter: Optional[str] = Field(None, max_length=50, description="장")
    section: Optional[str] = Field(None, max_length=50, description="절")
    is_deleted: int = Field(default=0, description="삭제 여부 (0: 유효, 1: 삭제)")
    is_tenant_protection: int = Field(default=0, description="임차인 보호 조항")
    is_tax_related: int = Field(default=0, description="세금 관련")
    is_delegation: int = Field(default=0, description="위임")
    is_penalty_related: int = Field(default=0, description="벌칙")
    chunk_ids: Optional[str] = Field(None, description="ChromaDB chunk ID 배열(json)")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="전체 메타데이터 (JSON)")


class ArticleCreate(ArticleBase):
    """조항 생성 스키마"""
    law_id: int = Field(..., description="법률 ID")


class ArticleUpdate(BaseModel):
    """조항 수정 스키마"""
    article_number: Optional[str] = Field(None, max_length=20)
    article_title: Optional[str] = Field(None, max_length=255)
    chapter: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=50)
    is_deleted: Optional[int] = None
    is_tenant_protection: Optional[int] = None
    is_tax_related: Optional[int] = None
    is_delegation: Optional[int] = None
    is_penalty_related: Optional[int] = None
    chunk_ids: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ArticleResponse(ArticleBase):
    """조항 응답 스키마"""
    article_id: int
    law_id: int
    references: List[LegalReferenceResponse] = Field(default_factory=list, description="법률 참조 목록")

    model_config = ConfigDict(from_attributes=True)


class ArticleSimpleResponse(ArticleBase):
    """조항 간단 응답 스키마 (참조 제외)"""
    article_id: int
    law_id: int

    model_config = ConfigDict(from_attributes=True)


# ==================== Law Schemas ====================

class LawBase(BaseModel):
    """법률 기본 스키마"""
    doc_type: str = Field(..., max_length=20, description="법률/시행령/시행규칙/대법원규칙/용어집/기타")
    title: str = Field(..., max_length=255, description="법령명")
    number: Optional[str] = Field(None, max_length=20, description="법령번호")
    enforcement_date: Optional[str] = Field(None, max_length=20, description="시행일")
    category: str = Field(..., max_length=50, description="카테고리")
    total_articles: int = Field(default=0, description="총 조항 수")
    last_article: Optional[str] = Field(None, max_length=20, description="마지막 조항 번호")
    source_file: Optional[str] = Field(None, description="원본 파일명")


class LawCreate(LawBase):
    """법률 생성 스키마"""
    pass


class LawUpdate(BaseModel):
    """법률 수정 스키마"""
    doc_type: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=255)
    number: Optional[str] = Field(None, max_length=20)
    enforcement_date: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    total_articles: Optional[int] = None
    last_article: Optional[str] = Field(None, max_length=20)
    source_file: Optional[str] = None


class LawResponse(LawBase):
    """법률 응답 스키마 (조항 포함)"""
    law_id: int
    created_at: datetime
    articles: List[ArticleSimpleResponse] = Field(default_factory=list, description="조항 목록")

    model_config = ConfigDict(from_attributes=True)


class LawSimpleResponse(LawBase):
    """법률 간단 응답 스키마 (조항 제외)"""
    law_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Search & Filter Schemas ====================

class LawSearchParams(BaseModel):
    """법률 검색 파라미터"""
    keyword: Optional[str] = Field(None, description="법령명 또는 법령번호 검색")
    doc_type: Optional[str] = Field(None, description="문서 타입 필터")
    category: Optional[str] = Field(None, description="카테고리 필터")
    skip: int = Field(default=0, ge=0, description="페이지네이션 오프셋")
    limit: int = Field(default=20, ge=1, le=100, description="페이지네이션 리미트")


class ArticleSearchParams(BaseModel):
    """조항 검색 파라미터"""
    law_id: Optional[int] = Field(None, description="법률 ID")
    article_number: Optional[str] = Field(None, description="조항 번호")
    chapter: Optional[str] = Field(None, description="장")
    is_tenant_protection: Optional[int] = Field(None, description="임차인 보호 조항 필터")
    is_tax_related: Optional[int] = Field(None, description="세금 관련 필터")
    is_deleted: int = Field(default=0, description="삭제된 조항 포함 여부")
    skip: int = Field(default=0, ge=0, description="페이지네이션 오프셋")
    limit: int = Field(default=20, ge=1, le=100, description="페이지네이션 리미트")


# ==================== Bulk Operations ====================

class LawBulkCreate(BaseModel):
    """법률 일괄 생성 스키마"""
    laws: List[LawCreate] = Field(..., description="생성할 법률 목록")


class ArticleBulkCreate(BaseModel):
    """조항 일괄 생성 스키마"""
    law_id: int = Field(..., description="법률 ID")
    articles: List[ArticleBase] = Field(..., description="생성할 조항 목록")
