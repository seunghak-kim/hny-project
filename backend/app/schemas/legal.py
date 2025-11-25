from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== Law Schemas =====
class LawBase(BaseModel):
    doc_type: str = Field(..., description="문서 유형 (법률/시행령/시행규칙/대법원규칙/용어집/기타)")
    title: str = Field(..., description="법률 제목")
    number: str = Field(..., description="법률 번호")
    enforcement_date: str = Field(..., description="시행일자")
    category: str = Field(..., description="카테고리")
    total_articles: int = Field(default=0, description="총 조항 수")
    last_article: str = Field(..., description="마지막 조항 번호")
    source_file: str = Field(..., description="원문 파일 경로")


class LawCreate(LawBase):
    pass


class LawUpdate(BaseModel):
    doc_type: Optional[str] = None
    title: Optional[str] = None
    number: Optional[str] = None
    enforcement_date: Optional[str] = None
    category: Optional[str] = None
    total_articles: Optional[int] = None
    last_article: Optional[str] = None
    source_file: Optional[str] = None


class LawResponse(LawBase):
    law_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Article Schemas =====
class ArticleBase(BaseModel):
    law_id: int
    article_number: str = Field(..., description="조항 번호")
    article_title: str = Field(..., description="조항 제목")
    chapter: Optional[str] = Field(None, description="장")
    section: Optional[str] = Field(None, description="절")
    is_deleted: bool = Field(default=False, description="삭제 여부")
    is_tenant_protection: bool = Field(default=False, description="임대차 보호법 여부")
    is_tax_related: bool = Field(default=False, description="세법 관련 여부")
    is_delegation: bool = Field(default=False, description="위임 여부")
    is_penalty_related: bool = Field(default=False, description="벌칙 관련 여부")
    chunk_ids: Optional[List[str]] = Field(None, description="FAISS chunk ID 배열")
    metadata_json: Optional[dict] = Field(None, description="메타데이터 JSON")


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    article_number: Optional[str] = None
    article_title: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    is_deleted: Optional[bool] = None
    is_tenant_protection: Optional[bool] = None
    is_tax_related: Optional[bool] = None
    is_delegation: Optional[bool] = None
    is_penalty_related: Optional[bool] = None
    chunk_ids: Optional[int] = None
    metadata_json: Optional[dict] = None


class ArticleResponse(ArticleBase):
    article_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== LegalReference Schemas =====
class LegalReferenceBase(BaseModel):
    law_id: int
    article_number: str = Field(..., description="조항 번호")
    article_title: str = Field(..., description="조항 제목")
    chapter: Optional[str] = Field(None, description="장")
    section: Optional[str] = Field(None, description="절")
    is_deleted: bool = Field(default=False, description="삭제 여부")
    is_tenant_protection: bool = Field(default=False, description="임대차 보호법 여부")
    is_tax_related: bool = Field(default=False, description="세법 관련 여부")
    is_delegation: bool = Field(default=False, description="위임 여부")
    is_penalty_related: bool = Field(default=False, description="벌칙 관련 여부")
    chunk_ids: Optional[List[str]] = Field(None, description="FAISS chunk ID 배열")
    metadata_json: Optional[dict] = Field(None, description="메타데이터 JSON")


class LegalReferenceCreate(LegalReferenceBase):
    article_id: int


class LegalReferenceResponse(LegalReferenceBase):
    article_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Combined Schemas =====
class LawWithArticles(LawResponse):
    articles: List[ArticleResponse] = []

    class Config:
        from_attributes = True


class ArticleWithLaw(ArticleResponse):
    law: Optional[LawResponse] = None

    class Config:
        from_attributes = True
