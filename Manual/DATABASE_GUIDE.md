# 데이터베이스 가이드

**버전**: 2.0
**작성일**: 2025-10-14
**최종 업데이트**: 2025-10-21 (Phase 1 Long-term Memory 반영)
**데이터베이스**: PostgreSQL 15+
**주요 변경사항**: user_id int 통일, chat_sessions.metadata 구조, Long-term Memory 구현

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

### 주요 테이블 (8개)

| 테이블명 | 행 수 (예상) | 용도 |
|---------|-------------|------|
| `users` | ~1,000 | 사용자 정보 ✅ |
| `chat_sessions` | ~10,000 | 채팅 세션 관리 (Phase 1 Long-term Memory) ✅ |
| `chat_messages` | ~100,000 | 채팅 메시지 저장 ✅ |
| `checkpoints` | ~50,000 | LangGraph 체크포인트 (PostgreSQL) ✅ |
| `legal_clauses` | ~500 | 법률 조항 (pgvector) |
| `real_estates` | ~10,000 | 부동산 매물 |
| `transactions` | ~11,000 | 거래 내역 |
| `trusts` | ~100 | 신탁 정보 |

---

## 🏗️ 스키마 구조

### ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    USERS ||--o{ CHAT_SESSIONS : creates
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
    CHECKPOINTS ||--o| CHAT_SESSIONS : tracks
    REAL_ESTATES ||--o{ TRANSACTIONS : has

    USERS {
        integer id PK
        varchar email UK
        varchar type
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    CHAT_SESSIONS {
        varchar session_id PK
        integer user_id FK
        varchar title
        text last_message
        integer message_count
        jsonb session_metadata
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    CHAT_MESSAGES {
        integer id PK
        varchar session_id FK
        varchar role
        text content
        jsonb structured_data
        timestamp created_at
    }

    CHECKPOINTS {
        text thread_id PK
        text checkpoint_id PK
        text parent_checkpoint_id
        bytea checkpoint
        bytea metadata
        timestamp created_at
    }

    REAL_ESTATES {
        integer id PK
        varchar property_type
        varchar region
        bigint price
        numeric area
        integer build_year
        varchar status
        timestamp created_at
    }

    TRANSACTIONS {
        integer id PK
        integer property_id FK
        varchar transaction_type
        bigint amount
        date transaction_date
    }
```

**Phase 1 Long-term Memory 구현 완료** ✅
- `chat_sessions.session_metadata` (JSONB): conversation_summary 저장
- `chat_messages`: 대화 히스토리 저장
- `users.id`: Integer 타입 (통일 완료)

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

### 1. Users (사용자 정보)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'admin'|'user'|'agent'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_type ON users(type);
```

**필드 설명**:
- `id`: **Integer Primary Key** (user_id 통일 완료) ✅
- `email`: 이메일 (Unique, 로그인용)
- `type`: 사용자 유형 (admin/user/agent)
- `is_active`: 활성화 상태

---

### 2. Chat Sessions (채팅 세션 관리)

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) DEFAULT '새 대화',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    session_metadata JSONB,  -- ✅ Phase 1: conversation_summary 저장
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);
```

**필드 설명**:
- `session_id`: 채팅 세션 ID (Primary Key)
- `user_id`: **Integer FK** (users.id) ✅
- `title`: 대화 제목 (자동 생성)
- `last_message`: 마지막 메시지 미리보기
- `message_count`: 메시지 개수
- **`session_metadata` (JSONB)**: Phase 1 Long-term Memory 저장소 ✅
  ```json
  {
    "conversation_summary": "강남구 아파트 전세 시세 조회 (5억~7억)",
    "last_updated": "2025-10-20T18:30:00",
    "message_count": 5,
    "summary_method": "simple"
  }
  ```
- `is_active`: 활성화 상태
- `updated_at`: 마지막 업데이트 시간 (정렬용)

---

### 3. Chat Messages (채팅 메시지)

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user'|'assistant'|'system'
    content TEXT NOT NULL,
    structured_data JSONB,  -- 구조화된 데이터 (sections 등)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

**필드 설명**:
- `id`: Auto-increment Primary Key
- `session_id`: FK (chat_sessions.session_id)
- `role`: 메시지 발신자 (user/assistant/system)
- `content`: 메시지 내용
- `structured_data`: 구조화된 응답 데이터 (JSON)

---

### 4. Checkpoints (LangGraph 체크포인트)

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
- `thread_id`: **chat_session_id** (대화창 ID, chat_sessions.session_id와 매핑) ✅
- `checkpoint_id`: 체크포인트 ID (LangGraph 자동 생성)
- `parent_checkpoint_id`: 부모 체크포인트 ID
- `checkpoint`: msgpack 직렬화된 MainSupervisorState
- `metadata`: 체크포인트 메타데이터

**Phase 1 변경사항** ✅:
- `thread_id`가 **chat_session_id**를 사용하도록 변경
- 이전: HTTP session_id (임시)
- 현재: chat_session_id (영구적, 대화창 단위)

---

### 5. Legal Clauses (법률 조항 - pgvector)

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

---

### 6. Real Estates (부동산 매물)

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

---

### 7. Transactions (거래 내역)

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

---

### 8. Long-term Memory 구현 (Phase 1) ✅

**현재 구현 방식**: Conversation Memories 테이블 없음

Phase 1에서는 별도 테이블 대신 **chat_sessions.session_metadata (JSONB)**를 사용합니다.

**저장 위치**: `chat_sessions.session_metadata`
```json
{
  "conversation_summary": "강남구 아파트 전세 시세 조회 (5억~7억)",
  "last_updated": "2025-10-20T18:30:00",
  "message_count": 5,
  "summary_method": "simple"
}
```

**로드 메서드**: `SimpleMemoryService.load_recent_memories()`
```python
# user_id 기반으로 최근 N개 세션의 요약 로드
memories = await memory_service.load_recent_memories(
    user_id=42,
    limit=5,  # settings.MEMORY_LOAD_LIMIT
    session_id="current-session-123"  # 현재 세션 제외
)
```

**저장 메서드**: `SimpleMemoryService.save_conversation()`
```python
# 대화 요약을 chat_sessions.session_metadata에 저장
await memory_service.save_conversation(
    user_id=42,
    session_id="session-abc-123",
    messages=[],
    summary="강남구 아파트 전세 시세 조회"
)
```

**Phase 2 계획** (별도 테이블 추가):
```sql
-- Phase 2에서 추가 예정
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100),
    summary TEXT,
    intent_type VARCHAR(50),
    teams_used JSONB,
    created_at TIMESTAMP
);
```

---

## 🔍 쿼리 예시

### 1. 채팅 세션 & 메시지 관리

```python
from app.models.chat import ChatSession, ChatMessage
from app.db.postgre_db import get_async_db

# 1. 채팅 세션 생성
async def create_chat_session(user_id: int, title: str = "새 대화"):
    async for db in get_async_db():
        session = ChatSession(
            session_id=f"session-{uuid.uuid4()}",
            user_id=user_id,
            title=title
        )
        db.add(session)
        await db.commit()
        return session

# 2. 채팅 메시지 저장
async def save_message(session_id: str, role: str, content: str):
    async for db in get_async_db():
        message = ChatMessage(
            session_id=session_id,
            role=role,  # 'user' or 'assistant'
            content=content
        )
        db.add(message)
        await db.commit()
        return message

# 3. 최근 메시지 조회 (Chat History)
async def get_recent_messages(session_id: str, limit: int = 6):
    async for db in get_async_db():
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return sorted(messages, key=lambda m: m.created_at)

# 4. 사용자의 모든 세션 조회
async def get_user_sessions(user_id: int):
    async for db in get_async_db():
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.is_active == True)
            .order_by(ChatSession.updated_at.desc())
        )
        return result.scalars().all()
```

### 2. Long-term Memory (Phase 1) ✅

```python
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
from app.db.postgre_db import get_async_db

# 1. 대화 요약 저장
async def save_conversation_summary(user_id: int, session_id: str, summary: str):
    async for db in get_async_db():
        memory_service = SimpleMemoryService(db)
        await memory_service.save_conversation(
            user_id=user_id,
            session_id=session_id,
            messages=[],  # Phase 1에서는 빈 리스트
            summary=summary
        )

# 2. 최근 대화 기록 로드
async def load_user_memories(user_id: int, current_session_id: str, limit: int = 5):
    async for db in get_async_db():
        memory_service = SimpleMemoryService(db)
        memories = await memory_service.load_recent_memories(
            user_id=user_id,
            limit=limit,
            session_id=current_session_id  # 현재 세션 제외
        )
        return memories
        # [
        #     {
        #         "session_id": "session-abc-123",
        #         "summary": "강남구 아파트 전세 시세 조회",
        #         "timestamp": "2025-10-20T14:30:00",
        #         "title": "강남구 전세 시세"
        #     },
        #     ...
        # ]

# 3. session_metadata 직접 조회 (디버깅용)
async def get_session_metadata(session_id: str):
    async for db in get_async_db():
        result = await db.execute(
            select(ChatSession.session_metadata)
            .where(ChatSession.session_id == session_id)
        )
        return result.scalar_one_or_none()
```

---

### 3. 법률 조항 벡터 검색

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

### 4. 부동산 시세 조회

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

## 📚 추가 참고 자료

- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/15/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [SQLAlchemy 비동기 문서](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg 문서](https://magicstack.github.io/asyncpg/current/)
- [STATE_MANAGEMENT_GUIDE.md](./STATE_MANAGEMENT_GUIDE.md) - State Management 가이드
- [SYSTEM_FLOW_DIAGRAM.md](./SYSTEM_FLOW_DIAGRAM.md) - 시스템 흐름도
- [simple_memory_service.py](../../backend/app/service_agent/foundation/simple_memory_service.py) - Long-term Memory 구현

---

**생성일**: 2025-10-14
**버전**: 2.0
**최종 업데이트**: 2025-10-21
**상태**: ✅ Phase 1 Long-term Memory 구현 완료

**주요 변경사항**:
- ✅ user_id 타입을 Integer로 통일
- ✅ chat_sessions, chat_messages 테이블 추가
- ✅ session_metadata (JSONB)를 통한 Long-term Memory 구현
- ✅ checkpoints 테이블의 thread_id를 chat_session_id로 변경
- ✅ SimpleMemoryService 사용 예시 추가
