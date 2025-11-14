# 🏠 홈즈냥즈 v1 - 시스템 문서

**부동산 AI 챗봇 "도와줘 홈즈냥즈"**

[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/holmesnyangz/beta_v001)
[![Architecture](https://img.shields.io/badge/architecture-LangGraph-green.svg)](https://www.langchain.com/langgraph)
[![WebSocket](https://img.shields.io/badge/protocol-WebSocket-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Database](https://img.shields.io/badge/database-PostgreSQL-blue.svg)](https://www.postgresql.org/)

---

## 📚 목차

- [시스템 개요](#-시스템-개요)
- [핵심 아키텍처](#-핵심-아키텍처)
- [주요 문서](#-주요-문서)
- [기술 스택](#-기술-스택)
- [실행 방법](#-실행-방법)
- [프로젝트 구조](#-프로젝트-구조)
- [개발 로드맵](#-개발-로드맵)

---

## 🎯 시스템 개요

### 프로젝트 소개

홈즈냥즈는 **LangGraph 기반 Multi-Agent 시스템**을 활용한 부동산 AI 상담 챗봇입니다.

- **실시간 WebSocket 통신**: 사용자와 AI 간의 양방향 실시간 커뮤니케이션
- **팀 기반 워크플로우**: Search, Analysis, Document 팀이 협업하여 작업 수행
- **프로그레스 플로우**: 실행 계획 및 진행 상황을 실시간으로 시각화
- **체크포인팅**: LangGraph의 상태 저장 기능으로 세션 복구 지원

### 핵심 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| **법률 상담** | 전세법, 임대차보호법 등 부동산 관련 법률 조회 | ✅ 구현 완료 |
| **시세 조회** | 지역별 매매가, 전세가, 월세 통계 | ✅ 구현 완료 |
| **매물 검색** | 개별 부동산 매물 검색 (아파트, 오피스텔 등) | ✅ 구현 완료 |
| **대출 상담** | 주택담보대출, 전세자금대출 정보 제공 | ✅ 구현 완료 |
| **계약서 작성** | 임대차 계약서 자동 생성 | ✅ 구현 완료 |
| **리스크 분석** | 부동산 투자 위험도 평가 | ✅ 구현 완료 |
| **Long-term Memory** | 사용자별 대화 기록 저장 및 맥락 제공 | 🔜 구현 예정 |

---

## 🏗️ 핵심 아키텍처

### 시스템 구조도

```mermaid
flowchart TB
    User([👤 사용자])

    subgraph Frontend["💻 Frontend (Next.js)"]
        UI[Chat Interface]
        Progress[Execution Progress]
    end

    subgraph Backend["🔧 Backend (FastAPI)"]
        WS[WebSocket Manager]
        Session[Session Manager]

        subgraph Supervisor["🎯 TeamBasedSupervisor"]
            Init[Initialize]
            Planning[Planning Node]
            Execute[Execute Teams]
            Aggregate[Aggregate Results]
            Response[Generate Response]
        end

        subgraph Teams["⚙️ Execution Teams"]
            Search[Search Team]
            Analysis[Analysis Team]
            Document[Document Team]
        end
    end

    subgraph Database["💾 Database (PostgreSQL)"]
        Sessions[(sessions)]
        Checkpoints[(checkpoints)]
        Memory[(conversation_memories)]
    end

    User --> UI
    UI <-->|WebSocket| WS
    WS --> Session
    WS --> Init

    Init --> Planning
    Planning --> Execute
    Execute --> Search
    Execute --> Analysis
    Execute --> Document
    Search --> Aggregate
    Analysis --> Aggregate
    Document --> Aggregate
    Aggregate --> Response

    Session -.-> Sessions
    Planning -.-> Checkpoints
    Response -.-> Memory

    Response -->|final_response| WS
    WS -->|WebSocket| Progress
```

### LLM 호출 지점 (10회)

| # | 위치 | 프롬프트 파일 | 목적 | Temperature |
|---|------|--------------|------|-------------|
| 1 | PlanningAgent | `intent_analysis.txt` | 사용자 의도 분석 | 0.0 |
| 2 | PlanningAgent | `agent_selection.txt` | Agent 선택 | 0.1 |
| 2b | PlanningAgent (fallback) | `agent_selection_simple.txt` | 단순 Agent 선택 | 0.3 |
| 3 | QueryDecomposer | `query_decomposition.txt` | 복합 질문 분해 | 0.1 |
| 4 | SearchExecutor | `keyword_extraction.txt` | 검색 키워드 추출 | 0.1 |
| 5 | SearchExecutor | `tool_selection_search.txt` | 검색 도구 선택 | 0.1 |
| 6 | AnalysisExecutor | `tool_selection_analysis.txt` | 분석 도구 선택 | 0.1 |
| 7-9 | Analysis Tools | 인라인 프롬프트 | 분석 & 인사이트 생성 | 0.3 |
| 10 | TeamSupervisor | `response_synthesis.txt` | 최종 응답 생성 | 0.3 |

### WebSocket 메시지 프로토콜

#### Server → Client

| 메시지 타입 | 발생 시점 | 필드 |
|------------|----------|------|
| `connected` | WebSocket 연결 | `session_id`, `timestamp` |
| `planning_start` | 계획 수립 시작 | `message` |
| `plan_ready` | 계획 수립 완료 | `intent`, `execution_steps`, `estimated_total_time` |
| `execution_start` | 작업 실행 시작 | `execution_steps`, `intent`, `confidence` |
| `todo_updated` | Step 상태 변경 | `execution_steps` (상태 업데이트됨) |
| `final_response` | 응답 생성 완료 | `response` (`type`, `answer`/`message`, `data`) |
| `error` | 에러 발생 | `error`, `timestamp` |

#### Client → Server

| 메시지 타입 | 필드 | 설명 |
|------------|------|------|
| `query` | `query`, `enable_checkpointing` | 사용자 질문 전송 |
| `interrupt_response` | `action`, `modified_todos` | Plan 승인/수정 (TODO) |
| `todo_skip` | `todo_id` | Todo 건너뛰기 (TODO) |

---

## 📖 주요 문서

### 1. 시스템 흐름도 (필독)

**파일**: [SYSTEM_FLOW_DIAGRAM.md](SYSTEM_FLOW_DIAGRAM.md)

**내용**:
- 전체 시스템 아키텍처 Mermaid 다이어그램
- LLM 호출 지점 상세 정리 (10회)
- WebSocket 메시지 프로토콜 전체 명세
- 시나리오별 처리 흐름 (IRRELEVANT, 단순 질문, 복합 질문)
- 최적화 포인트 및 성능 개선 전략
- 파일 구조 및 클래스 다이어그램

**핵심 내용**:
- ⚡ IRRELEVANT 조기 종료: LLM #2 생략으로 5초 → 0.6초 단축
- 📡 WebSocket 실시간 통신: Progress Flow UI로 투명성 향상
- 💾 Checkpointing: LangGraph 상태 저장으로 재연결 시 복구 가능

### 2. 데이터베이스 스키마 및 설정

**파일**:
- [DATABASE_SETUP_COMPLETE_GUIDE.md](DATABASE_SETUP_COMPLETE_GUIDE.md)
- [IMPORTANT_AUTO_TABLE_CREATION.md](IMPORTANT_AUTO_TABLE_CREATION.md)
- [database_schema_analysis_report.md](database_schema_analysis_report.md)

**내용**:
- PostgreSQL 데이터베이스 설정 가이드
- SQLAlchemy 모델 자동 테이블 생성
- 마이그레이션 가이드 (SQLite → PostgreSQL)

### 3. 세션 관리

**파일**:
- [session_vs_long_term_memory_explained.md](session_vs_long_term_memory_explained.md)
- [session_id_vs_user_id_clarification.md](session_id_vs_user_id_clarification.md)
- [SETUP_SESSIONS_TABLE.md](SETUP_SESSIONS_TABLE.md)

**내용**:
- Session ID vs User ID 차이점
- SessionManager 구현 (PostgreSQL 기반)
- 세션 만료 및 정리 메커니즘

### 4. Long-term Memory (구현 예정)

**파일**: [long_term_memory/IMPLEMENTATION_PLAN.md](long_term_memory/IMPLEMENTATION_PLAN.md)

**내용**:
- 사용자별 대화 기록 영구 저장
- 과거 맥락 제공으로 개인화된 AI 응답 생성
- 5개 Task로 구성된 구현 계획 (총 13-16시간 예상)

**데이터 모델**:
- `ConversationMemory`: 대화 기록
- `UserPreference`: 사용자 선호도
- `EntityMemory`: 엔티티 추적 (매물, 지역, 중개사)

### 5. TODO & Progress Flow

**파일**:
- [TODO_PROCESSFLOW_IMPLEMENTATION_COMPLETE.md](TODO_PROCESSFLOW_IMPLEMENTATION_COMPLETE.md)
- [TODO_PROCESSFLOW_INTEGRATION_PLAN.md](TODO_PROCESSFLOW_INTEGRATION_PLAN.md)

**내용**:
- 실시간 TODO 업데이트 시스템
- ExecutionPlanPage + ExecutionProgressPage 구현
- WebSocket을 통한 진행 상황 실시간 전송

### 6. Trust Score (신뢰도 점수)

**파일**: [trust_score_generation_completion_report.md](trust_score_generation_completion_report.md)

**내용**:
- 검색 결과 신뢰도 점수 계산 시스템
- 법률 조항, 시세, 대출 정보의 정확도 평가

### 7. Market Data Tool

**파일**: [complete_market_data_tool_implementation.md](complete_market_data_tool_implementation.md)

**내용**:
- PostgreSQL 기반 부동산 시세 조회 Tool
- 9,738개 매물, 10,772건 거래 내역 데이터
- 지역별 평균/최소/최대 매매가, 전세가, 월세 통계

---

## 💻 기술 스택

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 메인 언어 |
| **FastAPI** | 0.104+ | 웹 프레임워크 |
| **LangGraph** | 0.2+ | Multi-Agent 워크플로우 |
| **LangChain** | 0.1+ | LLM 통합 |
| **OpenAI API** | GPT-4o-mini | LLM 모델 |
| **PostgreSQL** | 15+ | 메인 데이터베이스 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Asyncpg** | 0.29+ | 비동기 PostgreSQL 드라이버 |
| **pgvector** | 0.2+ | 벡터 검색 (법률 검색) |
| **WebSockets** | - | 실시간 통신 |

### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| **Next.js** | 14+ | React 프레임워크 |
| **TypeScript** | 5+ | 타입 안전성 |
| **Tailwind CSS** | 3+ | 스타일링 |
| **WebSocket API** | - | 실시간 통신 |

### Database Schema

```sql
-- 주요 테이블
CREATE TABLE sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER,  -- ✅ Integer로 수정 완료
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    request_count INTEGER DEFAULT 0
);

-- Long-term Memory (구현 예정)
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
```

---

## 🚀 실행 방법

### 1. 환경 설정

```bash
# Python 가상환경 생성
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL Database
DATABASE_URL=postgresql://postgres:root1234@localhost:5432/real_estate

# App Settings
LOG_LEVEL=INFO
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 시작
# (Docker 사용 시)
docker run -d \
  --name postgres-holmesnyangz \
  -e POSTGRES_PASSWORD=root1234 \
  -e POSTGRES_DB=real_estate \
  -p 5432:5432 \
  postgres:15

# 테이블 생성 (자동)
# 서버 시작 시 SQLAlchemy가 자동으로 생성
```

### 4. 백엔드 실행

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**확인**:
- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5. 프론트엔드 실행 (선택)

```bash
cd frontend
npm install
npm run dev
```

**확인**:
- 프론트엔드: http://localhost:3000

### 6. WebSocket 테스트

```python
# Python WebSocket 클라이언트 테스트
import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8000/api/v1/chat/ws/test-session-id") as ws:
        # 메시지 수신 (connected)
        msg = await ws.recv()
        print("Connected:", json.loads(msg))

        # 쿼리 전송
        await ws.send(json.dumps({
            "type": "query",
            "query": "전세금 5% 인상 가능한가요?"
        }))

        # 응답 수신 (planning_start, plan_ready, execution_start, todo_updated, final_response)
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"[{data['type']}]", data)

            if data["type"] == "final_response":
                break

asyncio.run(test())
```

---

## 📁 프로젝트 구조

```
holmesnyangz/beta_v001/
├── backend/                           # 백엔드 (FastAPI)
│   ├── app/
│   │   ├── main.py                    # FastAPI 앱 진입점
│   │   ├── api/                       # API 엔드포인트
│   │   │   ├── chat_api.py           # WebSocket 채팅 API
│   │   │   ├── ws_manager.py         # WebSocket 연결 관리
│   │   │   ├── session_manager.py    # 세션 관리 (PostgreSQL)
│   │   │   └── schemas.py            # Pydantic 스키마
│   │   │
│   │   ├── models/                    # SQLAlchemy 모델
│   │   │   ├── session.py            # sessions 테이블
│   │   │   ├── users.py              # users 테이블
│   │   │   └── memory.py             # 🔜 Long-term Memory (구현 예정)
│   │   │
│   │   ├── service_agent/             # AI Agent 시스템
│   │   │   ├── supervisor/
│   │   │   │   └── team_supervisor.py  # TeamBasedSupervisor (LangGraph)
│   │   │   │
│   │   │   ├── cognitive_agents/
│   │   │   │   ├── planning_agent.py   # 의도 분석 & 실행 계획
│   │   │   │   └── query_decomposer.py # 복합 질문 분해
│   │   │   │
│   │   │   ├── execution_agents/
│   │   │   │   ├── search_executor.py   # 검색 팀 (법률, 시세, 대출)
│   │   │   │   ├── analysis_executor.py # 분석 팀 (리스크, 인사이트)
│   │   │   │   └── document_executor.py # 문서 팀 (계약서 작성)
│   │   │   │
│   │   │   ├── tools/                    # 검색 도구
│   │   │   │   ├── hybrid_legal_search.py   # 법률 검색 (pgvector)
│   │   │   │   ├── market_data_tool.py      # 시세 조회 (PostgreSQL)
│   │   │   │   ├── real_estate_search_tool.py # 매물 검색
│   │   │   │   └── loan_data_tool.py         # 대출 정보
│   │   │   │
│   │   │   ├── llm_manager/
│   │   │   │   ├── llm_service.py          # LLM 호출 관리
│   │   │   │   ├── prompt_manager.py       # 프롬프트 로드
│   │   │   │   └── prompts/                # 프롬프트 파일
│   │   │   │       ├── cognitive/          # 인지 에이전트 프롬프트
│   │   │   │       │   ├── intent_analysis.txt
│   │   │   │       │   ├── agent_selection.txt
│   │   │   │       │   └── query_decomposition.txt
│   │   │   │       └── execution/          # 실행 에이전트 프롬프트
│   │   │   │           ├── keyword_extraction.txt
│   │   │   │           ├── tool_selection_search.txt
│   │   │   │           └── response_synthesis.txt
│   │   │   │
│   │   │   └── foundation/
│   │   │       ├── separated_states.py     # State 정의
│   │   │       ├── checkpointer.py         # LangGraph Checkpointer
│   │   │       └── context.py              # LLM Context
│   │   │
│   │   ├── services/                      # 비즈니스 로직
│   │   │   └── long_term_memory_service.py # 🔜 구현 예정
│   │   │
│   │   ├── db/                            # 데이터베이스
│   │   │   └── postgre_db.py             # PostgreSQL 연결
│   │   │
│   │   └── reports/                       # 📄 문서 (여기!)
│   │       ├── README.md                  # 이 파일
│   │       ├── SYSTEM_FLOW_DIAGRAM.md     # 시스템 흐름도
│   │       └── long_term_memory/
│   │           └── IMPLEMENTATION_PLAN.md
│   │
│   ├── data/                              # 데이터 저장소
│   │   ├── system/
│   │   │   └── checkpoints/               # LangGraph 체크포인트
│   │   └── legal/                         # 법률 데이터
│   │
│   ├── migrations/                        # SQL 마이그레이션
│   │   └── create_sessions_table.sql
│   │
│   └── tests/                             # 테스트
│
└── frontend/                              # 프론트엔드 (Next.js)
    ├── components/
    │   ├── chat-interface.tsx
    │   ├── execution-plan-page.tsx
    │   └── execution-progress-page.tsx
    │
    └── lib/
        ├── ws.ts                          # WebSocket 클라이언트
        └── types.ts                       # TypeScript 타입
```

---

## 🗺️ 개발 로드맵

### Phase 1: Core System ✅ 완료

- [x] LangGraph 기반 Multi-Agent 아키텍처 구현
- [x] WebSocket 실시간 통신
- [x] Progress Flow UI (ExecutionPlanPage + ExecutionProgressPage)
- [x] Checkpointing (SQLite → PostgreSQL 마이그레이션 완료)
- [x] 법률 검색 (pgvector)
- [x] 시세 조회 (MarketDataTool)
- [x] 매물 검색 (RealEstateSearchTool)
- [x] Trust Score 시스템

### Phase 2: Long-term Memory 🔜 진행 예정

- [x] Task 1: sessions.user_id 타입 수정 ✅ 완료
- [ ] Task 2: Memory 모델 생성 (2시간)
- [ ] Task 3: LongTermMemoryService 구현 (4-5시간)
- [ ] Task 4: Workflow 통합 (3-4시간)
- [ ] Task 5: Frontend UI (4-5시간)

**예상 완료**: 2-3일 후

### Phase 3: Advanced Features ⏳ 계획 중

- [ ] Human-in-the-Loop (Plan 수정 기능)
- [ ] Todo Skip 기능
- [ ] 재연결 시 State 복구 (Checkpointing 활용)
- [ ] LLM 호출 병렬화 (성능 최적화)
- [ ] 결과 캐싱 (Redis)
- [ ] 패턴 기반 인사말 감지 (LLM 호출 생략)

### Phase 4: Production Ready ⏳ 계획 중

- [ ] 에러 처리 강화
- [ ] 모니터링 대시보드 (LLM 호출 통계)
- [ ] 응답 시간 분석
- [ ] 에러 추적 (Sentry)
- [ ] 테스트 커버리지 80% 이상
- [ ] CI/CD 파이프라인
- [ ] Docker 컨테이너화
- [ ] Kubernetes 배포

---

## 📊 시스템 메트릭스

### 성능 지표

| 시나리오 | LLM 호출 횟수 | 평균 응답 시간 | 최적화 전 | 최적화 후 |
|---------|--------------|---------------|----------|----------|
| **IRRELEVANT 쿼리** | 1회 | ~0.6초 | ~5초 | ⚡ 90% 단축 |
| **단순 부동산 질문** | 5회 | ~5-7초 | - | - |
| **복합 질문 + 분석** | 10회 | ~15-20초 | - | - |

### 데이터 통계 (2025-10-14 기준)

| 데이터 | 개수 |
|--------|------|
| **법률 조항** | ~500개 (pgvector 임베딩) |
| **부동산 매물** | 9,738개 |
| **거래 내역** | 10,772건 |
| **대출 상품** | ~50개 |

---

## 🛠️ 트러블슈팅

### 1. WebSocket 연결 실패

**증상**: `WebSocket connection failed: Session not found`

**해결**:
```bash
# 1. 세션 생성
curl -X POST http://localhost:8000/api/v1/chat/start

# 2. 반환된 session_id로 WebSocket 연결
ws://localhost:8000/api/v1/chat/ws/{session_id}
```

### 2. PostgreSQL 연결 오류

**증상**: `FATAL: password authentication failed for user "postgres"`

**해결**:
```bash
# .env 파일 확인
DATABASE_URL=postgresql://postgres:root1234@localhost:5432/real_estate

# PostgreSQL 접속 테스트
psql "postgresql://postgres:root1234@localhost:5432/real_estate"
```

### 3. LLM API 에러

**증상**: `openai.error.AuthenticationError: Invalid API key`

**해결**:
```bash
# .env 파일 확인
OPENAI_API_KEY=sk-...

# API Key 유효성 테스트
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 4. Checkpointer 초기화 실패

**증상**: `Failed to initialize checkpointer: Type is not msgpack serializable: function`

**해결**:
- 이미 해결됨! `_progress_callbacks`를 State에서 분리하여 별도 관리
- 자세한 내용: [SYSTEM_FLOW_DIAGRAM.md](SYSTEM_FLOW_DIAGRAM.md#progress-callback-메커니즘)

---

## 📞 문의 및 지원

- **Issues**: GitHub Issues 탭에서 버그 리포트 및 기능 요청
- **Discussions**: GitHub Discussions에서 질문 및 토론
- **Email**: support@holmesnyangz.com

---

## 📝 라이선스

This project is licensed under the MIT License.

---

## 🙏 감사의 말

- **LangChain & LangGraph**: Multi-Agent 워크플로우 프레임워크 제공
- **OpenAI**: GPT-4o-mini API 제공
- **FastAPI**: 고성능 웹 프레임워크 제공
- **PostgreSQL**: 안정적인 데이터베이스 제공

---

**Last Updated**: 2025-10-14
**Version**: 1.0.0
**Status**: 🚀 Production Ready (Phase 1 완료, Phase 2 진행 중)

---

## 🎉 Quick Start

```bash
# 1. 환경 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 수정: OPENAI_API_KEY, DATABASE_URL

# 3. PostgreSQL 시작 (Docker)
docker run -d \
  --name postgres-holmesnyangz \
  -e POSTGRES_PASSWORD=root1234 \
  -e POSTGRES_DB=real_estate \
  -p 5432:5432 \
  postgres:15

# 4. 서버 시작
uvicorn app.main:app --reload

# 5. 테스트
# http://localhost:8000/docs 접속
# WebSocket 연결: ws://localhost:8000/api/v1/chat/ws/{session_id}
```

**Welcome to 홈즈냥즈!** 🏠🐱
