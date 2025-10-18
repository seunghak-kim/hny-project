# 데이터베이스 가이드

**버전**: 1.0
**작성일**: 2025-10-14
**데이터베이스**: PostgreSQL 15+

---

## 📚 목차

- [데이터베이스 개요](#-데이터베이스-개요)
- [스키마 구조](#-스키마-구조)
- [설정 및 연결](#-설정-및-연결)
- [마이그레이션](#-마이그레이션)
- [데이터 모델](#-데이터-모델)
- [쿼리 예시](#-쿼리-예시)
- [백업 및 복구](#-백업-및-복구)
- [성능 최적화](#-성능-최적화)
- [트러블슈팅](#-트러블슈팅)

---

## 🎯 데이터베이스 개요

### 사용 데이터베이스

- **메인 DB**: PostgreSQL 15+
- **확장 기능**: pgvector (벡터 검색용)
- **ORM**: SQLAlchemy 2.0+
- **비동기 드라이버**: asyncpg

### 주요 데이터베이스

| 데이터베이스명 | 용도 | 크기 (예상) |
|--------------|------|-------------|
| `real_estate` | 메인 애플리케이션 데이터 | ~500MB |
| `postgres` | 시스템 기본 DB | ~10MB |

### 주요 테이블 (5개)

| 테이블명 | 행 수 (예상) | 용도 |
|---------|-------------|------|
| `sessions` | ~10,000 | 세션 관리 |
| `checkpoints` | ~50,000 | LangGraph 체크포인트 |
| `legal_clauses` | ~500 | 법률 조항 (pgvector) |
| `properties` | ~10,000 | 부동산 매물 |
| `transactions` | ~11,000 | 거래 내역 |

---

## 🏗️ 스키마 구조

### ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    SESSIONS ||--o{ CONVERSATION_MEMORIES : has
    USERS ||--o{ CONVERSATION_MEMORIES : creates
    USERS ||--o| USER_PREFERENCES : has
    PROPERTIES ||--o{ TRANSACTIONS : has
    PROPERTIES ||--o{ PROPERTY_NEARBY : has

    SESSIONS {
        varchar session_id PK
        integer user_id FK
        text metadata
        timestamp created_at
        timestamp expires_at
        timestamp last_activity
        integer request_count
    }

    USERS {
        integer id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        timestamp created_at
    }

    CONVERSATION_MEMORIES {
        uuid id PK
        integer user_id FK
        varchar session_id
        text user_query
        text assistant_response_summary
        varchar intent_type
        float intent_confidence
        jsonb teams_used
        jsonb entities_mentioned
        timestamp created_at
    }

    USER_PREFERENCES {
        integer id PK
        integer user_id FK
        jsonb preferred_regions
        jsonb preferred_property_types
        jsonb price_range
        integer interaction_count
        timestamp last_updated
    }

    PROPERTIES {
        integer id PK
        varchar property_type
        varchar region
        integer price
        float area
        integer build_year
        varchar status
        timestamp created_at
    }

    TRANSACTIONS {
        integer id PK
        integer property_id FK
        varchar transaction_type
        integer amount
        date transaction_date
    }
```

---

## ⚙️ 설정 및 연결

### 1. PostgreSQL 설치 (Docker)

```bash
# Docker로 PostgreSQL 시작
docker run -d \
  --name postgres-holmesnyangz \
  -e POSTGRES_PASSWORD=root1234 \
  -e POSTGRES_DB=real_estate \
  -p 5432:5432 \
  postgres:15

# pgvector 확장 설치
docker exec -it postgres-holmesnyangz psql -U postgres -d real_estate -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. 환경 변수 설정 (`.env`)

```bash
# PostgreSQL 연결 URL
DATABASE_URL=postgresql://postgres:root1234@localhost:5432/real_estate

# 또는 개별 설정
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root1234
POSTGRES_DB=real_estate

# 연결 풀 설정
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### 3. Python 연결 설정 (`postgre_db.py`)

```python
# backend/app/db/postgre_db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# 환경 변수에서 DATABASE_URL 읽기
DATABASE_URL = os.getenv("DATABASE_URL")

# 비동기 엔진 생성
engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30
)

# 비동기 세션 팩토리
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 데이터베이스 세션 의존성
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 4. 연결 테스트

```bash
# psql로 직접 연결
psql "postgresql://postgres:root1234@localhost:5432/real_estate"

# Python에서 테스트
python -c "
import asyncio
from app.db.postgre_db import engine

async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT version()')
        print(result.scalar())

asyncio.run(test())
"
```

---

## 🔄 마이그레이션

### SQLAlchemy 자동 테이블 생성

홈즈냥즈는 **자동 테이블 생성** 방식을 사용합니다.

**장점**:
- ✅ 코드 변경 시 자동으로 테이블 생성
- ✅ 마이그레이션 스크립트 불필요
- ✅ 개발 속도 향상

**단점**:
- ⚠️ 프로덕션 환경에서는 주의 필요 (데이터 손실 위험)

#### 1. 모델 정의 (`models/session.py`)

```python
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, nullable=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_activity = Column(TIMESTAMP(timezone=True), server_default=func.now())
    request_count = Column(Integer, default=0)
```

#### 2. 테이블 자동 생성 (`main.py`)

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from app.db.postgre_db import engine
from app.models import session, users  # 모든 모델 import

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 테이블 자동 생성"""
    async with engine.begin() as conn:
        # 모든 테이블 생성 (없으면)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 앱 종료 시 정리
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

### 수동 마이그레이션 (선택)

프로덕션 환경에서는 Alembic 사용 권장:

```bash
# Alembic 초기화
alembic init migrations

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 적용
alembic upgrade head
```

---

## 📊 데이터 모델

### 1. Sessions (세션 관리)

```sql
CREATE TABLE sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER,  -- ✅ Integer (User 테이블 FK)
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    request_count INTEGER DEFAULT 0
);

-- 인덱스
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

**필드 설명**:
- `session_id`: UUID 기반 세션 ID (Primary Key)
- `user_id`: 사용자 ID (로그인 시, 익명은 NULL)
- `metadata`: 추가 세션 정보 (JSON 형식 TEXT)
- `expires_at`: 세션 만료 시간 (기본 24시간)
- `request_count`: 요청 횟수 (rate limiting용)

### 2. Checkpoints (LangGraph 체크포인트)

```sql
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint BYTEA,
    metadata BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- 인덱스
CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id);
```

**필드 설명**:
- `thread_id`: 세션 ID (session_id와 동일)
- `checkpoint_id`: 체크포인트 ID (LangGraph 생성)
- `checkpoint`: msgpack 직렬화된 State
- `metadata`: 체크포인트 메타데이터

### 3. Legal Clauses (법률 조항 - pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE legal_clauses (
    id SERIAL PRIMARY KEY,
    law_title VARCHAR(255) NOT NULL,
    article_number VARCHAR(50),
    article_title TEXT,
    content TEXT NOT NULL,
    chapter VARCHAR(255),
    section VARCHAR(255),
    is_tenant_protection BOOLEAN DEFAULT FALSE,
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- pgvector 인덱스 (HNSW)
CREATE INDEX idx_legal_clauses_embedding ON legal_clauses
USING hnsw (embedding vector_cosine_ops);

-- 기타 인덱스
CREATE INDEX idx_legal_clauses_law_title ON legal_clauses(law_title);
CREATE INDEX idx_legal_clauses_tenant ON legal_clauses(is_tenant_protection);
```

**필드 설명**:
- `embedding`: 1536차원 벡터 (OpenAI text-embedding-3-small)
- `is_tenant_protection`: 임차인 보호 관련 조항 여부
- HNSW 인덱스: 빠른 벡터 유사도 검색 (ANN)

### 4. Properties (부동산 매물)

```sql
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    property_type VARCHAR(50) NOT NULL,  -- APARTMENT, OFFICETEL, VILLA
    region VARCHAR(100) NOT NULL,
    address TEXT,
    price BIGINT NOT NULL,
    area NUMERIC(10, 2),  -- ㎡
    rooms INTEGER,
    bathrooms INTEGER,
    build_year INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    elevator BOOLEAN,
    parking BOOLEAN,
    agent_name VARCHAR(255),
    agent_phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, SOLD, RESERVED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_properties_region ON properties(region);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_area ON properties(area);
CREATE INDEX idx_properties_status ON properties(status);
```

### 5. Transactions (거래 내역)

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,  -- SALE, LEASE, MONTHLY
    amount BIGINT NOT NULL,
    transaction_date DATE NOT NULL,
    exclusive_area NUMERIC(10, 2),  -- 전용면적
    floor INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_transactions_property ON transactions(property_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
```

### 6. Conversation Memories (Long-term Memory) 🔜 구현 예정

```sql
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100),
    user_query TEXT NOT NULL,
    assistant_response_summary TEXT,
    conversation_summary TEXT,
    intent_type VARCHAR(50),
    intent_confidence FLOAT,
    teams_used JSONB,
    entities_mentioned JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_memories_user ON conversation_memories(user_id);
CREATE INDEX idx_memories_created ON conversation_memories(created_at DESC);
CREATE INDEX idx_memories_user_created ON conversation_memories(user_id, created_at DESC);
CREATE INDEX idx_memories_intent ON conversation_memories(intent_type);
```

---

## 🔍 쿼리 예시

### 1. 세션 관리

```python
# 세션 생성
from app.models.session import Session
from app.db.postgre_db import AsyncSessionLocal

async def create_session(session_id: str, user_id: int = None):
    async with AsyncSessionLocal() as db:
        session = Session(
            session_id=session_id,
            user_id=user_id,
            expires_at=datetime.now() + timedelta(hours=24)
        )
        db.add(session)
        await db.commit()
        return session

# 세션 조회
async def get_session(session_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()

# 만료된 세션 삭제
async def cleanup_expired_sessions():
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(Session).where(Session.expires_at < func.now())
        )
        await db.commit()
```

### 2. 법률 조항 벡터 검색

```python
# pgvector 유사도 검색
from pgvector.asyncpg import register_vector

async def search_legal_clauses(query_embedding: list, limit: int = 10):
    async with AsyncSessionLocal() as db:
        # pgvector 확장 등록
        await register_vector(db.connection())

        result = await db.execute(
            text("""
                SELECT id, law_title, article_number, content,
                       1 - (embedding <=> :embedding) as similarity
                FROM legal_clauses
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """),
            {"embedding": query_embedding, "limit": limit}
        )
        return result.fetchall()
```

### 3. 부동산 시세 조회

```python
# 지역별 평균 시세
async def get_average_price_by_region(region: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                func.avg(Property.price).label("avg_price"),
                func.min(Property.price).label("min_price"),
                func.max(Property.price).label("max_price"),
                func.count().label("count")
            )
            .where(Property.region == region)
            .where(Property.status == "ACTIVE")
        )
        return result.one()

# 거래 내역 통계
async def get_transaction_stats(region: str, transaction_type: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                func.avg(Transaction.amount).label("avg_amount"),
                func.count().label("count")
            )
            .join(Property)
            .where(Property.region == region)
            .where(Transaction.transaction_type == transaction_type)
            .where(Transaction.transaction_date >= date.today() - timedelta(days=365))
        )
        return result.one()
```

---

## 💾 백업 및 복구

### 1. 백업

```bash
# 전체 데이터베이스 백업
pg_dump -U postgres -d real_estate > backup_$(date +%Y%m%d).sql

# 특정 테이블만 백업
pg_dump -U postgres -d real_estate -t sessions -t checkpoints > sessions_backup.sql

# 압축 백업
pg_dump -U postgres -d real_estate | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 2. 복구

```bash
# SQL 파일에서 복구
psql -U postgres -d real_estate < backup_20251014.sql

# 압축 파일에서 복구
gunzip -c backup_20251014.sql.gz | psql -U postgres -d real_estate
```

### 3. 자동 백업 스크립트 (Cron)

```bash
# /home/user/backup_db.sh
#!/bin/bash
BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업
pg_dump -U postgres -d real_estate | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# 7일 이상 된 백업 삭제
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete

# Cron 등록 (매일 새벽 2시)
# crontab -e
# 0 2 * * * /home/user/backup_db.sh
```

---

## ⚡ 성능 최적화

### 1. 인덱스 최적화

```sql
-- 자주 사용하는 쿼리 패턴에 인덱스 추가
CREATE INDEX idx_properties_region_price ON properties(region, price);
CREATE INDEX idx_transactions_date_type ON transactions(transaction_date, transaction_type);

-- Partial 인덱스 (활성 매물만)
CREATE INDEX idx_properties_active ON properties(region, price) WHERE status = 'ACTIVE';
```

### 2. 연결 풀 설정

```python
# backend/app/db/postgre_db.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # 기본 연결 수
    max_overflow=10,       # 추가 연결 수
    pool_timeout=30,       # 연결 대기 시간
    pool_recycle=3600,     # 연결 재사용 주기 (1시간)
    echo=False             # SQL 로그 비활성화 (프로덕션)
)
```

### 3. 쿼리 성능 분석

```sql
-- 쿼리 실행 계획 확인
EXPLAIN ANALYZE
SELECT * FROM properties
WHERE region = '강남구' AND price < 500000000
ORDER BY price DESC
LIMIT 10;

-- 인덱스 사용 확인
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 4. Vacuum 및 Analyze

```sql
-- 자동 Vacuum 설정 확인
SHOW autovacuum;

-- 수동 Vacuum (데이터 정리)
VACUUM ANALYZE sessions;
VACUUM ANALYZE properties;

-- Full Vacuum (디스크 공간 회수)
VACUUM FULL properties;
```

---

## 🔧 트러블슈팅

### 1. 연결 오류

**증상**: `FATAL: password authentication failed`

**해결**:
```bash
# pg_hba.conf 확인
docker exec -it postgres-holmesnyangz cat /var/lib/postgresql/data/pg_hba.conf

# 패스워드 재설정
docker exec -it postgres-holmesnyangz psql -U postgres -c "ALTER USER postgres PASSWORD 'root1234';"
```

### 2. pgvector 확장 오류

**증상**: `ERROR: extension "vector" is not available`

**해결**:
```bash
# Docker 컨테이너에 pgvector 설치
docker exec -it postgres-holmesnyangz apt-get update
docker exec -it postgres-holmesnyangz apt-get install -y postgresql-15-pgvector

# 확장 생성
docker exec -it postgres-holmesnyangz psql -U postgres -d real_estate -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. 느린 쿼리

**증상**: 특정 쿼리가 5초 이상 소요

**해결**:
```sql
-- 1. EXPLAIN ANALYZE로 분석
EXPLAIN ANALYZE SELECT ...;

-- 2. 인덱스 추가
CREATE INDEX idx_xxx ON table_name(column);

-- 3. 통계 정보 업데이트
ANALYZE table_name;
```

### 4. 디스크 공간 부족

**증상**: `ERROR: could not extend file: No space left on device`

**해결**:
```bash
# 디스크 사용량 확인
df -h

# 테이블 크기 확인
psql -U postgres -d real_estate -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"

# 불필요한 데이터 삭제 + Vacuum
DELETE FROM sessions WHERE expires_at < NOW() - INTERVAL '30 days';
VACUUM FULL sessions;
```

---

## 📚 참고 자료

- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/15/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [SQLAlchemy 비동기 문서](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg 문서](https://magicstack.github.io/asyncpg/current/)

---

**생성일**: 2025-10-14
**버전**: 1.0
**상태**: ✅ 프로덕션 준비 완료
