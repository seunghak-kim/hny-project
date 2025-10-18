-- Legal Metadata Database Schema
-- Created: 2025-10-01
-- Purpose: Fast metadata queries and ChromaDB search filtering

-- =============================================================================
-- Table 1: laws - 법령 기본 정보
-- =============================================================================
CREATE TABLE IF NOT EXISTS laws (
    law_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT NOT NULL,              -- 법률/시행령/시행규칙/대법원규칙/용어집/기타
    title TEXT NOT NULL,                 -- 법령명
    number TEXT,                         -- 법령번호
    enforcement_date TEXT,               -- 시행일
    category TEXT NOT NULL,              -- 카테고리 (1_공통 매매_임대차, 2_임대차_전세_월세, 3_공급_및_관리_매매_분양, 4_기타)
    total_articles INTEGER DEFAULT 0,   -- 총 조항 수
    last_article TEXT,                   -- 마지막 조항 번호
    source_file TEXT,                    -- 원본 파일명
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, number, doc_type)
);

-- =============================================================================
-- Table 2: articles - 조항 상세 정보
-- =============================================================================
CREATE TABLE IF NOT EXISTS articles (
    article_id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id INTEGER NOT NULL,
    article_number TEXT NOT NULL,        -- 조항 번호 (예: 제1조) - 본문/부칙 중복 가능
    article_title TEXT,                  -- 조항 제목
    chapter TEXT,                        -- 장
    section TEXT,                        -- 절
    is_deleted INTEGER DEFAULT 0,        -- 삭제 여부 (0=유효, 1=삭제)
    is_tenant_protection INTEGER DEFAULT 0,  -- 임차인 보호 조항
    is_tax_related INTEGER DEFAULT 0,    -- 세금 관련
    is_delegation INTEGER DEFAULT 0,     -- 위임
    is_penalty_related INTEGER DEFAULT 0, -- 벌칙
    chunk_ids TEXT,                      -- FAISS chunk ID 배열 (JSON) - 고유 매칭 키
    metadata_json TEXT,                  -- 전체 메타데이터 (JSON)
    FOREIGN KEY (law_id) REFERENCES laws(law_id)
    -- UNIQUE(law_id, article_number) 제거: 본문/부칙 제1조 구분 위해
    -- 고유성은 chunk_ids가 보장
);

-- =============================================================================
-- Table 3: legal_references - 법령 간 참조 관계
-- =============================================================================
CREATE TABLE IF NOT EXISTS legal_references (
    reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_article_id INTEGER NOT NULL,
    reference_type TEXT NOT NULL,        -- law_references, decree_references, form_references
    target_law_title TEXT,               -- 참조 대상 법령명
    target_article_number TEXT,          -- 참조 대상 조항
    reference_text TEXT,                 -- 원본 참조 텍스트
    FOREIGN KEY (source_article_id) REFERENCES articles(article_id)
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Laws table indexes
CREATE INDEX IF NOT EXISTS idx_laws_doc_type ON laws(doc_type);
CREATE INDEX IF NOT EXISTS idx_laws_enforcement_date ON laws(enforcement_date);
CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category);
CREATE INDEX IF NOT EXISTS idx_laws_title ON laws(title);

-- Articles table indexes
CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id);
CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number);
CREATE INDEX IF NOT EXISTS idx_articles_deleted ON articles(is_deleted);
CREATE INDEX IF NOT EXISTS idx_articles_tenant ON articles(is_tenant_protection);
CREATE INDEX IF NOT EXISTS idx_articles_tax ON articles(is_tax_related);
CREATE INDEX IF NOT EXISTS idx_articles_delegation ON articles(is_delegation);
CREATE INDEX IF NOT EXISTS idx_articles_penalty ON articles(is_penalty_related);

-- References table indexes
CREATE INDEX IF NOT EXISTS idx_references_source ON legal_references(source_article_id);
CREATE INDEX IF NOT EXISTS idx_references_type ON legal_references(reference_type);

-- =============================================================================
-- Usage Notes
-- =============================================================================

/*
Database Statistics (2025-10-01):
- Total Laws: 28
- Total Articles: 1,552
- Document Types:
  • 법률: 9 (32%)
  • 시행령: 7 (25%)
  • 시행규칙: 7 (25%)
  • 대법원규칙: 2 (7%)
  • 용어집: 1 (4%)
  • 기타: 2 (7%)

Categories:
  • 1_공통 매매_임대차: 9
  • 3_공급_및_관리_매매_분양: 8
  • 4_기타: 6
  • 2_임대차_전세_월세: 5

Special Articles:
  • Tenant Protection: 28
  • Delegation: 156
  • Penalty Related: 1
  • Tax Related: 0

Common Queries:
1. Get law information:
   SELECT * FROM laws WHERE title LIKE '%공인중개사법%';

2. Get all articles of a law:
   SELECT a.* FROM articles a
   JOIN laws l ON a.law_id = l.law_id
   WHERE l.title = '공인중개사법' AND a.is_deleted = 0;

3. Find tenant protection articles:
   SELECT a.*, l.title FROM articles a
   JOIN laws l ON a.law_id = l.law_id
   WHERE a.is_tenant_protection = 1;

4. Get laws by category:
   SELECT * FROM laws WHERE category = '2_임대차_전세_월세';

5. Find laws by enforcement date range:
   SELECT * FROM laws
   WHERE enforcement_date BETWEEN '2024.01.01' AND '2024.12.31'
   ORDER BY enforcement_date;
*/
