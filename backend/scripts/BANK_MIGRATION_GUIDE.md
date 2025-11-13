# Bank Data PostgreSQL Migration Guide

은행 금융 상품 JSON 데이터를 PostgreSQL로 마이그레이션하는 가이드입니다.

## 📋 목차
- [데이터 구조](#데이터-구조)
- [데이터베이스 스키마](#데이터베이스-스키마)
- [마이그레이션 절차](#마이그레이션-절차)
- [사용 예시](#사용-예시)

---

## 데이터 구조

### JSON 파일 구조
`backend/data/bank/` 디렉토리에는 다음과 같은 JSON 파일들이 있습니다:

```
backend/data/bank/
├── bank.hana.json      (하나은행)
├── bank.k.json         (케이뱅크)
├── bank.kakao.json     (카카오뱅크)
├── bank.kb.json        (KB국민은행)
├── bank.sc.json        (SC제일은행)
├── bank.sinhan.json    (신한은행)
└── bank.woori.json     (우리은행)
```

### 각 JSON 파일의 구조
```json
[
  {
    "_id": {"$oid": "..."},
    "metadata": {
      "product_id": "SC-mortgage-FirstHomeLoan-01",
      "bank_name": "SC제일은행",
      "product_name": "퍼스트홈론",
      "product_category": "주택담보대출",
      "last_updated": "2025-09-17",
      "source_document_url": "https://...",
      "summary": "상품 요약..."
    },
    "content_chunks": [
      {
        "chunk_id": "SC-mortgage-FirstHomeLoan-01-C01",
        "category": "자격조건",
        "content_text": "만 19세 이상 소득증빙이 가능한 고객...",
        "keywords": ["소득증빙", "주택 소유", "CSS", "대출 자격"]
      }
    ]
  }
]
```

---

## 데이터베이스 스키마

### ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│     banks       │
├─────────────────┤
│ id (PK)         │
│ bank_name       │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ▼
┌─────────────────────────┐         ┌──────────────────────┐
│      products           │         │  product_categories  │
├─────────────────────────┤         ├──────────────────────┤
│ id (PK)                 │         │ id (PK)              │
│ product_id (UNIQUE)     │         │ category_name        │
│ bank_id (FK)            │◄────────│ description          │
│ product_category_id (FK)│         │ created_at           │
│ product_name            │         └──────────────────────┘
│ summary                 │
│ source_document_url     │
│ last_updated            │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
        │
        │ 1:N
        ▼
┌──────────────────────┐         ┌──────────────────────┐
│  content_chunks      │         │  chunk_categories    │
├──────────────────────┤         ├──────────────────────┤
│ id (PK)              │         │ id (PK)              │
│ chunk_id (UNIQUE)    │         │ category_name        │
│ product_id (FK)      │         │ created_at           │
│ chunk_category_id(FK)│◄────────└──────────────────────┘
│ content_text         │
│ created_at           │
└──────────────────────┘
        │
        │ M:N
        ▼
┌──────────────────────┐         ┌──────────────────────┐
│  chunk_keywords      │         │     keywords         │
├──────────────────────┤         ├──────────────────────┤
│ chunk_id (FK, PK)    │◄────────│ id (PK)              │
│ keyword_id (FK, PK)  │         │ keyword (UNIQUE)     │
│ created_at           │         │ created_at           │
└──────────────────────┘         └──────────────────────┘
```

### 테이블 설명

#### 1. banks (은행 마스터)
은행 정보를 저장하는 마스터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| bank_name | VARCHAR(100) | 은행명 (unique) |
| created_at | TIMESTAMP | 생성일시 |
| updated_at | TIMESTAMP | 수정일시 |

#### 2. product_categories (상품 카테고리 마스터)
금융 상품의 카테고리 (주택담보대출, 전세자금대출, 서민금융 등)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| category_name | VARCHAR(100) | 카테고리명 (unique) |
| description | TEXT | 설명 |
| created_at | TIMESTAMP | 생성일시 |

#### 3. products (금융 상품)
각 은행의 금융 상품 정보

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| product_id | VARCHAR(100) | 원본 상품 ID (unique) |
| bank_id | INTEGER | 은행 ID (FK) |
| product_category_id | INTEGER | 상품 카테고리 ID (FK) |
| product_name | VARCHAR(255) | 상품명 |
| summary | TEXT | 상품 요약 |
| source_document_url | TEXT | 출처 URL |
| last_updated | DATE | 최종 업데이트 날짜 |
| created_at | TIMESTAMP | 생성일시 |
| updated_at | TIMESTAMP | 수정일시 |

#### 4. chunk_categories (청크 카테고리 마스터)
상품 상세 정보의 카테고리 (자격조건, 대출한도, 대출금리 등)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| category_name | VARCHAR(100) | 카테고리명 (unique) |
| created_at | TIMESTAMP | 생성일시 |

#### 5. content_chunks (상품 상세 정보)
각 상품의 상세 정보 청크

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| chunk_id | VARCHAR(100) | 원본 청크 ID (unique) |
| product_id | INTEGER | 상품 ID (FK) |
| chunk_category_id | INTEGER | 청크 카테고리 ID (FK) |
| content_text | TEXT | 상세 내용 |
| created_at | TIMESTAMP | 생성일시 |

#### 6. keywords (키워드 마스터)
전체 키워드 마스터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | Primary Key |
| keyword | VARCHAR(255) | 키워드 (unique) |
| created_at | TIMESTAMP | 생성일시 |

#### 7. chunk_keywords (청크-키워드 관계)
청크와 키워드의 다대다 관계

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| chunk_id | INTEGER | 청크 ID (FK, PK) |
| keyword_id | INTEGER | 키워드 ID (FK, PK) |
| created_at | TIMESTAMP | 생성일시 |

### 인덱스
성능 최적화를 위해 다음 인덱스가 생성됩니다:

- 외래 키 인덱스
- Full-text search 인덱스 (한국어)
  - `content_chunks.content_text`
  - `products.product_name`
  - `products.summary`

---

## 마이그레이션 절차

### 1. 데이터베이스 준비

PostgreSQL 데이터베이스가 준비되어 있어야 합니다.

```bash
# PostgreSQL 데이터베이스 생성 (psql에서)
CREATE DATABASE your_database_name;
```

### 2. 스키마 생성

SQL 스크립트를 실행하여 테이블을 생성합니다.

```bash
psql -U postgres -d real_estate -f backend/scripts/create_bank_schema.sql
```

또는 Python에서:

```python
import psycopg2

conn = psycopg2.connect(
    dbname='your_database_name',
    user='your_username',
    password='your_password',
    host='localhost'
)
cursor = conn.cursor()

with open('backend/scripts/create_bank_schema.sql', 'r') as f:
    cursor.execute(f.read())

conn.commit()
conn.close()
```

### 3. 한국어 전문 검색 설정 (선택사항)

기본 스키마는 'simple' 전문 검색 구성을 사용합니다. 한국어 텍스트 검색 성능을 향상시키려면:

**방법 1: pg_trgm 사용 (권장)**
```bash
psql -U postgres -d real_estate -f backend/scripts/setup_korean_fulltext_search.sql
```

이 방법은 trigram 유사도 검색을 사용하여 한국어 텍스트에서 잘 작동합니다.

**검색 예시:**
```sql
-- LIKE 검색 (인덱스 지원)
SELECT * FROM products WHERE product_name ILIKE '%주택%';

-- 유사도 검색
SELECT * FROM products
WHERE similarity(product_name, '전세대출') > 0.3
ORDER BY similarity(product_name, '전세대출') DESC;
```

**방법 2: pg_korean 확장 사용**

pg_korean 확장이 설치되어 있다면 `setup_korean_fulltext_search.sql` 파일의 주석을 해제하여 사용할 수 있습니다.

### 4. 마이그레이션 스크립트 설정

`backend/scripts/migrate_bank_data.py` 파일에서 데이터베이스 설정을 업데이트합니다:

```python
DB_CONFIG = {
    'dbname': 'your_database_name',      # 실제 DB 이름
    'user': 'your_username',              # 실제 사용자명
    'password': 'your_password',          # 실제 비밀번호
    'host': 'localhost',                  # 실제 호스트
    'port': 5432
}
```

### 5. 의존성 설치

```bash
cd backend
pip install psycopg2-binary
```

### 6. 마이그레이션 실행

스크립트의 DB_CONFIG를 먼저 설정한 후:

```bash
cd backend
python scripts/migrate_bank_data.py
```

실행 시 확인 메시지가 나타나며, `yes`를 입력하면 마이그레이션이 시작됩니다.

**예상 출력:**
```
==================================================
Bank Data Migration to PostgreSQL
==================================================

Found 7 JSON files to migrate:
  - bank.hana.json
  - bank.k.json
  - bank.kakao.json
  - bank.kb.json
  - bank.sc.json
  - bank.sinhan.json
  - bank.woori.json

Processing: bank.sc.json
  Found 14 products
  ✓ Product: 퍼스트홈론
    + 7 chunks
...

✓ Migration completed successfully!

Database Statistics:
  - 은행 (banks): 7
  - 상품 카테고리 (product_categories): 3
  - 금융 상품 (products): 140
  - 청크 카테고리 (chunk_categories): 8
  - 상세 정보 청크 (content_chunks): 980
  - 키워드 (keywords): 450
  - 청크-키워드 관계 (chunk_keywords): 2,450
```

---

## 사용 예시

### 마이그레이션 완료 후 데이터 조회 예시

#### 1. 특정 은행의 상품 목록 조회

```sql
SELECT
    p.product_name,
    p.summary,
    pc.category_name
FROM products p
JOIN banks b ON p.bank_id = b.id
JOIN product_categories pc ON p.product_category_id = pc.id
WHERE b.bank_name = 'SC제일은행'
ORDER BY p.product_name;
```

#### 2. 키워드로 상품 검색

```sql
SELECT DISTINCT
    b.bank_name,
    p.product_name,
    p.summary
FROM products p
JOIN banks b ON p.bank_id = b.id
JOIN content_chunks cc ON cc.product_id = p.id
JOIN chunk_keywords ck ON ck.chunk_id = cc.id
JOIN keywords k ON k.id = ck.keyword_id
WHERE k.keyword LIKE '%LTV%'
ORDER BY b.bank_name, p.product_name;
```

#### 3. 상품 상세 정보 조회

```sql
SELECT
    p.product_name,
    cc_cat.category_name,
    cc.content_text,
    ARRAY_AGG(k.keyword) as keywords
FROM products p
JOIN content_chunks cc ON cc.product_id = p.id
JOIN chunk_categories cc_cat ON cc.chunk_category_id = cc_cat.id
LEFT JOIN chunk_keywords ck ON ck.chunk_id = cc.id
LEFT JOIN keywords k ON k.id = ck.keyword_id
WHERE p.product_id = 'SC-mortgage-FirstHomeLoan-01'
GROUP BY p.product_name, cc_cat.category_name, cc.content_text, cc.id
ORDER BY cc.id;
```

#### 4. Full-text Search (전문 검색)

```sql
-- 한국어 전문 검색
SELECT
    b.bank_name,
    p.product_name,
    cc_cat.category_name,
    cc.content_text,
    ts_rank(to_tsvector('korean', cc.content_text), query) AS rank
FROM products p
JOIN banks b ON p.bank_id = b.id
JOIN content_chunks cc ON cc.product_id = p.id
JOIN chunk_categories cc_cat ON cc.chunk_category_id = cc_cat.id,
     to_tsquery('korean', '주택 & 대출') as query
WHERE to_tsvector('korean', cc.content_text) @@ query
ORDER BY rank DESC
LIMIT 10;
```

#### 5. 카테고리별 상품 수 통계

```sql
SELECT
    b.bank_name,
    pc.category_name,
    COUNT(*) as product_count
FROM products p
JOIN banks b ON p.bank_id = b.id
JOIN product_categories pc ON p.product_category_id = pc.id
GROUP BY b.bank_name, pc.category_name
ORDER BY b.bank_name, product_count DESC;
```

---

## 데이터 모델의 장점

### 1. 정규화
- 중복 데이터 최소화
- 데이터 일관성 유지
- 업데이트 이상(anomaly) 방지

### 2. 확장성
- 새로운 은행 추가 용이
- 새로운 상품 카테고리 추가 용이
- 키워드 관리 효율적

### 3. 검색 성능
- 인덱스를 통한 빠른 검색
- Full-text search 지원
- 키워드 기반 검색 최적화

### 4. 유지보수성
- 명확한 관계 구조
- 외래 키를 통한 참조 무결성
- 자동 타임스탬프 관리

---

## 추가 개선 사항

### 1. 버전 관리
상품 정보가 변경될 때 이력을 추적하고 싶다면:

```sql
CREATE TABLE product_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100),
    old_data JSONB,
    new_data JSONB
);
```

### 2. 검색 로그
사용자 검색 패턴 분석을 위해:

```sql
CREATE TABLE search_logs (
    id SERIAL PRIMARY KEY,
    search_query TEXT,
    search_filters JSONB,
    result_count INTEGER,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER
);
```

### 3. 상품 평점/리뷰
사용자 피드백을 위해:

```sql
CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    user_id INTEGER,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 문제 해결

### 1. 한국어 전문 검색 구성 오류

**오류 메시지:**
```
오류: "korean" 전문 검색 구성이 없음
```

**해결 방법:**

이미 수정된 `create_bank_schema.sql`은 'simple' 구성을 사용하므로 이 오류가 발생하지 않습니다. 만약 발생한다면:

**옵션 1: pg_trgm 사용 (권장)**
```bash
psql -U postgres -d real_estate -f backend/scripts/setup_korean_fulltext_search.sql
```

**옵션 2: 인덱스 제거**
```sql
DROP INDEX IF EXISTS idx_content_chunks_text_search;
DROP INDEX IF EXISTS idx_products_name_search;
DROP INDEX IF EXISTS idx_products_summary_search;
```

**옵션 3: 한국어 검색 확장 설치**
- pg_korean 또는 다른 한국어 형태소 분석기 설치 필요
- 설치 후 `setup_korean_fulltext_search.sql`의 주석 해제

### 2. Migration 실패 시

**일반적인 원인:**
1. 데이터베이스 연결 정보 확인
2. PostgreSQL 서버 실행 상태 확인
3. 권한 확인 (CREATE, INSERT 권한 필요)
4. 로그 확인

**연결 오류 해결:**
```python
# migrate_bank_data.py의 DB_CONFIG 확인
DB_CONFIG = {
    'dbname': 'real_estate',      # 실제 DB 이름
    'user': 'postgres',            # 실제 사용자명
    'password': 'your_password',   # 실제 비밀번호
    'host': 'localhost',
    'port': 5432
}
```

**권한 확인:**
```sql
-- 사용자 권한 확인
SELECT * FROM information_schema.role_table_grants
WHERE grantee = 'postgres';

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE real_estate TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
```

### 3. JSON 파일 인코딩 오류

**오류:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**해결:**
JSON 파일이 UTF-8로 인코딩되어 있는지 확인합니다.

```bash
# 파일 인코딩 확인
file -I backend/data/bank/*.json

# UTF-8로 변환 (필요시)
iconv -f EUC-KR -t UTF-8 input.json > output.json
```

### 4. 성능 이슈 시

**데이터베이스 최적화:**
```sql
-- 통계 정보 업데이트 및 정리
VACUUM ANALYZE;

-- 인덱스 재구성
REINDEX DATABASE real_estate;

-- 특정 테이블만 재인덱스
REINDEX TABLE products;
```

**쿼리 성능 확인:**
```sql
-- 쿼리 실행 계획 확인
EXPLAIN ANALYZE
SELECT * FROM products WHERE product_name ILIKE '%주택%';

-- 느린 쿼리 로그 활성화 (postgresql.conf)
log_min_duration_statement = 1000  # 1초 이상 걸리는 쿼리 로그
```

### 5. 중복 데이터 오류

**오류:**
```
duplicate key value violates unique constraint
```

**원인:**
마이그레이션을 여러 번 실행하거나 데이터가 중복된 경우

**해결:**
```sql
-- 기존 데이터 확인
SELECT COUNT(*) FROM banks;
SELECT COUNT(*) FROM products;

-- 전체 데이터 삭제 후 재마이그레이션
TRUNCATE banks, products, content_chunks, keywords CASCADE;

-- 또는 전체 재생성
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
```

---

## 라이센스 및 주의사항

- 금융 상품 정보는 각 은행의 저작권이 있을 수 있습니다
- 실제 서비스에서는 최신 정보로 주기적 업데이트가 필요합니다
- 개인정보가 포함되지 않도록 주의하세요
