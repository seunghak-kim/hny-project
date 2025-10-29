# 부동산 AI 시스템 흐름도 v2.2

**버전**: 2.2
**작성일**: 2025-10-10
**최종 업데이트**: 2025-10-22 (3-Tier Hybrid Memory, Agent Routing 개선 반영)
**주요 변경사항**:
- 3-Tier Hybrid Memory (Short/Mid/Long-term)
- Agent Priority 정렬 (251021_Agent Routing.md)
- Session Deletion 버그 수정 (251021_SESSION_DELETE_FIX.md)
- Spinner 동작 개선 (251021_SPINNER_FIX.md)
- Enum 직렬화 수정 (251020_ENUM_FIX.md)

---

## 🔄 주요 버전 변경점

### v1 → v2 (WebSocket 실시간 통신)

| 항목 | v1 | v2 |
|------|----|----|
| **통신 방식** | HTTP POST | WebSocket (실시간) |
| **응답 방식** | 동기식 (완료 후 응답) | 스트리밍 (progress_callback) |
| **프론트엔드** | 단순 로딩 스피너 | ExecutionPlanPage + ExecutionProgressPage |
| **State 관리** | In-memory | LangGraph Checkpointing (PostgreSQL) |
| **Todo 관리** | 없음 | 실시간 todo 업데이트 (pending → in_progress → completed) |

### v2.0 → v2.1 (Long-term Memory)

| 항목 | v2.0 | v2.1 |
|------|------|------|
| **Memory 범위** | 현재 대화창만 (Chat History) | Hybrid Memory (Chat History + Long-term) |
| **세션 ID** | session_id (WebSocket) | + chat_session_id (대화창) |
| **user_id 타입** | Optional[str] | **Optional[int]** ✅ 통일 |
| **Memory 저장** | 없음 | chat_sessions.metadata (JSONB) |
| **Memory 로드** | 없음 | planning_node에서 최근 N개 세션 로드 |
| **설정 가능** | - | MEMORY_LOAD_LIMIT (0~10+) |

### v2.1 → v2.2 (3-Tier Hybrid Memory + 개선 사항)

| 항목 | v2.1 | v2.2 |
|------|------|------|
| **Memory 전략** | 단일 레벨 (recent) | **3-Tier (Short/Mid/Long-term)** |
| **Sessions 1-5** | 요약만 로드 | **전체 메시지 로드** (상세 컨텍스트) |
| **Sessions 6-10** | 요약만 로드 | **LLM 요약 로드** (Mid-term) |
| **Sessions 11-20** | 로드 안함 | **LLM 요약 로드** (Long-term) |
| **토큰 제한** | 없음 | **2000 tokens** (tiktoken 기반) |
| **백그라운드 요약** | 없음 | **Fire-and-forget 패턴** |
| **Agent 실행 순서** | 랜덤 (set 사용) | **Priority 정렬** (step.priority) |
| **병렬 실행 Spinner** | ❌ 작동 안함 | ✅ **todo_updated 전송** |
| **Session 삭제** | ❌ 500 Error | ✅ **정상 동작** (thread_id 수정) |
| **Enum 직렬화** | ❌ 에러 발생 | ✅ **.value 사용** |

---

## 전체 시스템 아키텍처 (LLM 호출 지점 + Memory 통합 표시)

```mermaid
flowchart TD
    User([👤 사용자])

    %% ============================================
    %% 1. WebSocket Layer
    %% ============================================
    subgraph WSLayer["🔌 WebSocket Layer"]
        WSEndpoint["/ws/{session_id}"]
        ConnMgr["ConnectionManager<br/>- active_connections<br/>- message_queue"]
        SessMgr["SessionManager<br/>- session_id 생성<br/>- 세션 검증"]

        WSEndpoint --> ConnMgr
        WSEndpoint --> SessMgr
    end

    User -->|WebSocket 연결| WSEndpoint

    %% ============================================
    %% 2. Supervisor (LangGraph)
    %% ============================================
    subgraph Supervisor["🎯 TeamBasedSupervisor (LangGraph)"]
        direction TB
        InitNode["initialize_node<br/>⚙️ 상태 초기화"]
        PlanningNode["planning_node<br/>🧠 의도 분석 & 계획<br/>+ 🧠 Memory 로딩"]
        RouteNode{"route_after_planning<br/>🔀 라우팅"}
        ExecuteNode["execute_teams_node<br/>⚙️ 팀 실행<br/>(Priority 순서 보장)"]
        AggregateNode["aggregate_results_node<br/>📊 결과 통합"]
        ResponseNode["generate_response_node<br/>📝 응답 생성<br/>+ 💾 Memory 저장"]

        InitNode --> PlanningNode
        PlanningNode --> RouteNode
        RouteNode -->|execution_steps 있음| ExecuteNode
        RouteNode -->|execution_steps 없음<br/>또는 IRRELEVANT/UNCLEAR| ResponseNode
        ExecuteNode --> AggregateNode
        AggregateNode --> ResponseNode
    end

    ConnMgr -->|query 수신| InitNode

    %% ============================================
    %% 2.5 Checkpointing (PostgreSQL)
    %% ============================================
    subgraph Checkpoint["💾 Checkpointing"]
        PostgresCheckpoint["AsyncPostgresSaver<br/>PostgreSQL<br/>- checkpoints (thread_id)<br/>- checkpoint_writes<br/>- checkpoint_blobs"]
    end

    PlanningNode -.->|상태 저장<br/>(thread_id)| PostgresCheckpoint
    ExecuteNode -.->|상태 저장| PostgresCheckpoint
    AggregateNode -.->|상태 저장| PostgresCheckpoint

    %% ============================================
    %% 2.6 Memory System (3-Tier Hybrid)
    %% ============================================
    subgraph MemorySystem["🧠 3-Tier Hybrid Memory"]
        direction TB
        MemoryDB["PostgreSQL<br/>chat_sessions.session_metadata"]

        subgraph MemoryTiers["메모리 계층"]
            ShortTerm["Short-term (1-5)<br/>📄 전체 메시지<br/>(상세 컨텍스트)"]
            MidTerm["Mid-term (6-10)<br/>📝 LLM 요약<br/>(중기 기억)"]
            LongTerm["Long-term (11-20)<br/>📝 LLM 요약<br/>(장기 기억)"]
        end

        TokenLimit["토큰 제한<br/>2000 tokens<br/>(tiktoken)"]

        MemoryDB --> ShortTerm
        MemoryDB --> MidTerm
        MemoryDB --> LongTerm
        ShortTerm --> TokenLimit
        MidTerm --> TokenLimit
        LongTerm --> TokenLimit
    end

    PlanningNode -->|load_tiered_memories| MemoryDB
    ResponseNode -->|save + background summarize| MemoryDB

    %% ============================================
    %% 3. Planning Agent (키워드 필터 추가)
    %% ============================================
    subgraph PlanningAgentFile["🧠 PlanningAgent"]
        direction TB
        AnalyzeIntent["analyze_intent<br/>🤖 LLM #1<br/>intent_analysis.txt"]
        IntentCheck{intent_type?}
        SkipAgent["⚡ Skip Agent Selection<br/>(IRRELEVANT/UNCLEAR)"]
        KeywordFilter["🔍 Keyword Filter<br/>(LEGAL_CONSULT/<br/>MARKET_INQUIRY)"]
        SuggestAgent["suggest_agents<br/>🤖 LLM #2<br/>agent_selection.txt"]
        QueryDecomp["QueryDecomposer<br/>🤖 LLM #3<br/>query_decomposition.txt"]
        CreatePlan["create_execution_plan<br/>📋 실행 계획 생성<br/>(Priority 할당)"]

        AnalyzeIntent --> IntentCheck
        IntentCheck -->|IRRELEVANT<br/>or UNCLEAR| SkipAgent
        IntentCheck -->|LEGAL_CONSULT<br/>or MARKET_INQUIRY| KeywordFilter
        IntentCheck -->|정상| SuggestAgent
        KeywordFilter -->|단순 질문| CreatePlan
        KeywordFilter -->|복잡한 질문| SuggestAgent
        SkipAgent --> CreatePlan
        SuggestAgent --> QueryDecomp
        QueryDecomp --> CreatePlan
    end

    PlanningNode --> AnalyzeIntent
    CreatePlan --> RouteNode

    %% ============================================
    %% 4. Execution Agents (병렬 실행 개선)
    %% ============================================
    subgraph Executors["⚙️ Execution Agents"]
        direction LR

        subgraph Search["SearchExecutor<br/>(Priority 0)"]
            SearchKW["🤖 LLM #4<br/>keyword_extraction"]
            SearchTool["🤖 LLM #5<br/>tool_selection_search"]
            SearchTools["🔧 Tools<br/>Legal/Market/Loan"]
        end

        subgraph Analysis["AnalysisExecutor<br/>(Priority 1)"]
            AnalysisTool["🤖 LLM #6<br/>tool_selection_analysis"]
            AnalysisTools["🔧 Tools<br/>Contract/Market"]
            AnalysisLLM["🤖 LLM #7-#9<br/>분석 & 종합"]
        end

        subgraph Document["DocumentExecutor<br/>(Priority 2)"]
            DocGen["문서 생성"]
        end
    end

    ExecuteNode --> Search
    ExecuteNode --> Analysis
    ExecuteNode --> Document

    Search --> AggregateNode
    Analysis --> AggregateNode
    Document --> AggregateNode

    %% ============================================
    %% 5. Progress Callbacks (병렬 실행 개선)
    %% ============================================
    subgraph Callbacks["📡 Progress Callbacks"]
        CB1["planning_start<br/>'계획을 수립하고 있습니다...'"]
        CB2["plan_ready<br/>{intent, execution_steps,<br/>estimated_total_time}"]
        CB3["execution_start<br/>(ExecutionProgressPage 생성)"]
        CB4["todo_updated<br/>{execution_steps<br/>with updated status}<br/>✅ 병렬 실행도 전송"]
        CB5["final_response<br/>{type, content, data}"]
    end

    AnalyzeIntent -.->|callback| CB1
    CreatePlan -.->|callback| CB2
    ExecuteNode -.->|callback| CB3
    Search -.->|callback (순차)| CB4
    Analysis -.->|callback (순차)| CB4
    ExecuteNode -.->|callback (병렬)| CB4
    ResponseNode -.->|callback| CB5

    CB1 -.->|send_message| ConnMgr
    CB2 -.->|send_message| ConnMgr
    CB3 -.->|send_message| ConnMgr
    CB4 -.->|send_message| ConnMgr
    CB5 -.->|send_message| ConnMgr

    %% ============================================
    %% 6. Response Generation (Memory 요약 포함)
    %% ============================================
    RespCheck{intent_type?}
    Guidance["_generate_out_of_scope_response<br/>안내 메시지"]
    LLMResp["_generate_llm_response<br/>🤖 LLM #10<br/>response_synthesis.txt"]
    SimpleResp["_generate_simple_response<br/>단순 응답"]
    MemorySave["💾 Memory 저장<br/>1. save_conversation<br/>2. 🤖 LLM #11 (background)<br/>   conversation_summary.txt"]

    ResponseNode --> RespCheck
    RespCheck -->|IRRELEVANT<br/>or UNCLEAR| Guidance
    RespCheck -->|결과 있음| LLMResp
    RespCheck -->|결과 없음| SimpleResp

    Guidance --> MemorySave
    LLMResp --> MemorySave
    SimpleResp --> MemorySave

    MemorySave -.->|callback| CB5
    MemorySave -.->|async save| MemoryDB

    %% ============================================
    %% 7. Frontend
    %% ============================================
    ConnMgr -->|WebSocket 메시지| User

    %% ============================================
    %% Styling
    %% ============================================
    classDef llmNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef wsNode fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dbNode fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef skipNode fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef memoryNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef newNode fill:#e0f7fa,stroke:#00838f,stroke-width:3px

    class AnalyzeIntent,SuggestAgent,QueryDecomp,SearchKW,SearchTool,AnalysisTool,AnalysisLLM,LLMResp llmNode
    class WSEndpoint,ConnMgr,CB1,CB2,CB3,CB4,CB5 wsNode
    class PostgresCheckpoint,MemoryDB dbNode
    class SkipAgent skipNode
    class MemorySystem,MemoryTiers,ShortTerm,MidTerm,LongTerm,TokenLimit,MemorySave memoryNode
    class KeywordFilter,CB4 newNode
```

---

## LLM 호출 지점 상세 정리

### 📊 LLM 호출 통계 (v2.2 업데이트)

| # | 호출 위치 | 프롬프트 파일 | 모델 | Temperature | 호출 방식 | 목적 |
|---|----------|-------------|------|-------------|----------|------|
| 1 | PlanningAgent | `intent_analysis.txt` | GPT-4o-mini | 0.0 | async | 사용자 의도 분석 |
| 2 | PlanningAgent | `agent_selection.txt` | GPT-4o-mini | 0.0 | async | Agent 선택 (키워드 필터 우선⚡) |
| 2b | PlanningAgent (fallback) | `agent_selection_simple.txt` | GPT-4o-mini | 0.0 | async | 단순 Agent 선택 |
| 3 | QueryDecomposer | `query_decomposition.txt` | GPT-4o-mini | 0.1 | async | 복합 질문 분해 |
| 4 | SearchExecutor | `keyword_extraction.txt` | GPT-4o-mini | 0.1 | **sync** | 검색 키워드 추출 |
| 5 | SearchExecutor | `tool_selection_search.txt` | GPT-4o-mini | 0.1 | async | 검색 도구 선택 |
| 6 | AnalysisExecutor | `tool_selection_analysis.txt` | GPT-4o-mini | 0.0 | async | 분석 도구 선택 |
| 7 | ContractAnalysisTool | ⚠️ 인라인 프롬프트 | GPT-4o-mini | 0.3 | async | 계약서 분석 |
| 8 | MarketAnalysisTool | `insight_generation.txt` | GPT-4o-mini | 0.3 | async | 시장 인사이트 생성 |
| 9 | AnalysisExecutor | `insight_generation.txt` | GPT-4o-mini | 0.3 | async | 분석 인사이트 종합 |
| 10 | TeamSupervisor | `response_synthesis.txt` | GPT-4o-mini | 0.3 | async | 최종 응답 생성 |
| **11** | **SimpleMemoryService** | **`conversation_summary.txt`** | **GPT-4o-mini** | **0.3** | **async (background)** | **✨ 대화 요약 생성** |

### 📁 프롬프트 파일 위치 (v2.2 추가)

#### Cognitive Prompts (인지 에이전트)
```
backend/app/service_agent/llm_manager/prompts/cognitive/
├── intent_analysis.txt          ✅ 사용됨 (LLM #1)
├── agent_selection.txt          ✅ 사용됨 (LLM #2, 키워드 필터 후 호출)
├── agent_selection_simple.txt   ✅ 사용됨 (LLM #2b, fallback)
├── query_decomposition.txt      ✅ 사용됨 (LLM #3)
└── plan_generation.txt          ❌ 미사용
```

#### Execution Prompts (실행 에이전트)
```
backend/app/service_agent/llm_manager/prompts/execution/
├── keyword_extraction.txt       ✅ 사용됨 (LLM #4)
├── tool_selection_search.txt    ✅ 사용됨 (LLM #5)
├── tool_selection_analysis.txt  ✅ 사용됨 (LLM #6)
├── insight_generation.txt       ✅ 사용됨 (LLM #8, #9)
└── response_synthesis.txt       ✅ 사용됨 (LLM #10)
```

#### Common Prompts (✨ v2.2 추가)
```
backend/app/service_agent/llm_manager/prompts/common/
├── conversation_summary.txt     ✅ 사용됨 (LLM #11, background)
└── error_response.txt           ❌ 미사용
```

#### ⚠️ 누락된 프롬프트 파일
- `contract_analysis.txt` - ContractAnalysisTool에서 인라인 프롬프트 사용 중

---

## 📡 WebSocket 메시지 프로토콜 (v2.2 업데이트)

### Client → Server

| 메시지 타입 | 필드 | 설명 |
|------------|------|------|
| `query` | `query`, `enable_checkpointing` | 사용자 쿼리 전송 |
| `interrupt_response` | `action`, `modified_todos` | Plan 승인/수정 (TODO) |
| `todo_skip` | `todo_id` | Todo 건너뛰기 (TODO) |

### Server → Client (✨ execution_start 추가)

| 메시지 타입 | 발생 시점 | 필드 | 프론트엔드 동작 |
|------------|----------|------|---------------|
| `connected` | WebSocket 연결 시 | - | 연결 확인 |
| `planning_start` | planning_node 시작 | `message` | 스피너 표시 |
| `plan_ready` | planning_node 완료 | `intent`, `confidence`, `execution_steps`, `estimated_total_time`, `keywords` | ExecutionPlanPage 생성 |
| **`execution_start`** | **execute_teams_node 시작** | **`message`, `execution_steps`, `intent`, `keywords`** | **ExecutionProgressPage 생성** |
| `todo_created` | 초기 todo 생성 | `execution_steps` | (미사용) |
| `todo_updated` | Step 상태 변경 | `execution_steps` | **✅ 병렬 실행도 전송**<br/>ExecutionProgressPage의 steps 업데이트 |
| `step_start` | Step 시작 | `agent`, `task` | (현재 미사용) |
| `step_progress` | Step 진행 중 | `progress_percentage` | (현재 미사용) |
| `step_complete` | Step 완료 | `result` | (현재 미사용) |
| `final_response` | generate_response_node 완료 | `response` (content/answer/message) | Progress 제거<br/>답변 표시<br/>idle 전환 |
| `error` | 에러 발생 | `error` | 에러 메시지 표시<br/>idle 전환 |

---

## 🔄 주요 처리 흐름 (시나리오별, v2.2 업데이트)

### 1. IRRELEVANT 쿼리 (빠른 경로) ⚡

```
사용자: "안녕" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: initialize_node
   └─ State 초기화 (LLM 호출 없음)
   ↓
planning_node
   ├─ 🧠 Memory 로드 (user_id 있으면)
   │  └─ load_tiered_memories() → 3-Tier 메모리 로드 (토큰 제한)
   ├─ 🤖 LLM #1: intent_analysis → IRRELEVANT
   ├─ ⚡ Skip LLM #2 (agent_selection) - 키워드 필터도 생략
   └─ create_execution_plan → Empty Plan (execution_steps: [])
   ↓
route_after_planning (라우팅 결정, LLM 호출 없음)
   └─ if intent_type == "irrelevant" → return "respond"
   ↓
⚡ execute_teams_node 건너뛰기 (바로 generate_response_node로)
⚡ aggregate_results_node 건너뛰기
   ↓
generate_response_node
   ├─ if intent_type == "irrelevant":
   ├─ _generate_out_of_scope_response() → 안내 메시지 (LLM 호출 없음)
   └─ 💾 Memory 저장 생략 (IRRELEVANT는 저장 안함)
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 안내 메시지 표시
```

**거치는 노드**: initialize → planning → route → generate_response → END
**건너뛴 노드**: ❌ execute_teams, ❌ aggregate

**WebSocket 메시지**:
1. `planning_start` → 스피너 표시
2. `plan_ready` (execution_steps: []) → ExecutionPlanPage 생성 시도 (빈 배열)
3. `final_response` (type: "guidance") → 안내 메시지 표시

**LLM 호출**: 1회만 (LLM #1: intent_analysis)
**Memory**: 로드만 (저장 안함)
**소요 시간**: ~0.6초

---

### 2. 단순 부동산 질문 (일반 경로, 키워드 필터 적용) ⚡

```
사용자: "공인중개사 금지행위는?" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: initialize_node
   └─ State 초기화
   ↓
planning_node
   ├─ 🧠 Memory 로드 (3-Tier)
   ├─ 🤖 LLM #1: intent_analysis → LEGAL_CONSULT
   │
   ├─ 🔍 Keyword Filter (LEGAL_CONSULT 경로)
   │  ├─ 분석 키워드 체크: ["비교", "분석", "계산", "평가", ...]
   │  └─ "금지행위는?" → 단순 질문 (분석 불필요)
   │  └─ ⚡ return ["search_team"] - LLM #2 생략!
   │
   └─ create_execution_plan → Simple Plan (1 step, priority: 0)
   ↓
route_after_planning
   └─ if execution_steps 있음 → return "execute"
   ↓
execute_teams_node
   ├─ execution_start 전송 → ExecutionProgressPage 생성
   ├─ strategy = "sequential" (순차 실행)
   ├─ Priority 정렬: [search (0)] ✅
   ├─ SearchTeam 시작 → ✅ todo_updated (step 0: in_progress)
   │  ├─ 🤖 LLM #4: keyword_extraction
   │  ├─ 🤖 LLM #5: tool_selection_search
   │  └─ Tools 실행 (LegalSearchTool, LLM 호출 없음)
   └─ SearchTeam 완료 → ✅ todo_updated (step 0: completed)
   ↓
aggregate_results_node
   └─ 결과 통합 (LLM 호출 없음)
   ↓
generate_response_node
   ├─ if 결과 있음:
   ├─ 🤖 LLM #10: response_synthesis → 최종 답변
   ├─ 💾 Memory 저장 (save_conversation)
   └─ 🤖 LLM #11: 백그라운드 요약 (Fire-and-forget)
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 답변 표시
```

**거치는 노드**: initialize → planning → route → execute_teams → aggregate → generate_response → END
**모든 노드 통과** ✅

**WebSocket 메시지**:
1. `planning_start`
2. `plan_ready` (execution_steps: [{ step_id, team: "search", status: "pending", priority: 0, ... }])
3. **`execution_start`** (ExecutionProgressPage 생성)
4. `todo_updated` (step 0: "in_progress") ✅
5. `todo_updated` (step 0: "completed") ✅
6. `final_response` (type: "summary", content: "...")

**LLM 호출**: 5회 (⚡ LLM #2 키워드 필터로 생략)
- LLM #1 (intent), LLM #4 (keyword), LLM #5 (tool), LLM #10 (response), LLM #11 (background summary)
**Memory**: 로드 + 저장 + 백그라운드 요약
**소요 시간**: ~5-7초

---

### 3. 복합 질문 + 분석 (전체 경로, 병렬 실행) ⚡

```
사용자: "강남구 아파트 시세 확인하고 투자 분석해줘" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: initialize_node
   └─ State 초기화
   ↓
planning_node
   ├─ 🧠 Memory 로드 (3-Tier)
   │  ├─ Short-term (1-5): 전체 메시지 (max 10 messages/session)
   │  ├─ Mid-term (6-10): LLM 요약
   │  ├─ Long-term (11-20): LLM 요약
   │  └─ 토큰 제한: 2000 tokens (tiktoken 기반)
   │
   ├─ 🤖 LLM #1: intent_analysis → MARKET_INQUIRY
   ├─ 🔍 Keyword Filter (MARKET_INQUIRY 경로)
   │  ├─ 분석 키워드 체크: ["비교", "분석", "평가", ...]
   │  └─ "분석해줘" → 복잡한 질문 (분석 필요)
   │  └─ 🤖 LLM #2: agent_selection → ["search_team", "analysis_team"]
   │
   ├─ 🤖 LLM #3: query_decomposition (복합 질문 분해)
   └─ create_execution_plan → Complex Plan
      ├─ step 0: search_team (priority: 0) ✅
      └─ step 1: analysis_team (priority: 1) ✅
   ↓
route_after_planning
   └─ if execution_steps 있음 → return "execute"
   ↓
execute_teams_node
   ├─ execution_start 전송 → ExecutionProgressPage 생성
   ├─ strategy = "parallel" or "sequential"
   ├─ Priority 정렬: [search (0), analysis (1)] ✅ 순서 보장
   │
   ├─ ===== 순차 실행 예시 =====
   ├─ SearchTeam 시작 → ✅ todo_updated (step 0: in_progress)
   │  ├─ 🤖 LLM #4: keyword_extraction
   │  ├─ 🤖 LLM #5: tool_selection_search
   │  └─ Tools 실행 (MarketDataTool, LLM 호출 없음)
   │  └─ SearchTeam 완료 → ✅ todo_updated (step 0: completed)
   │
   └─ AnalysisTeam 시작 → ✅ todo_updated (step 1: in_progress)
      ├─ 🤖 LLM #6: tool_selection_analysis
      ├─ MarketAnalysisTool
      │  └─ 🤖 LLM #8: insight_generation
      ├─ 🤖 LLM #9: insight_generation (분석 결과 종합)
      └─ AnalysisTeam 완료 → ✅ todo_updated (step 1: completed)
   │
   ├─ ===== 병렬 실행 예시 (v2.2 개선) =====
   ├─ SearchTeam & AnalysisTeam 병렬 시작
   ├─ ✅ todo_updated (step 0: in_progress) - 병렬 실행도 전송
   ├─ ✅ todo_updated (step 1: in_progress) - 병렬 실행도 전송
   ├─ (각 팀 작업 진행...)
   ├─ ✅ todo_updated (step 0: completed)
   └─ ✅ todo_updated (step 1: completed)
   ↓
aggregate_results_node
   └─ Search + Analysis 결과 통합 (LLM 호출 없음)
   ↓
generate_response_node
   ├─ if 결과 있음:
   ├─ 🤖 LLM #10: response_synthesis → 최종 답변
   ├─ 💾 Memory 저장 (save_conversation)
   └─ 🤖 LLM #11: 백그라운드 요약 (Fire-and-forget)
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 답변 표시
```

**거치는 노드**: initialize → planning → route → execute_teams → aggregate → generate_response → END
**모든 노드 통과** ✅

**WebSocket 메시지** (병렬 실행):
1. `planning_start`
2. `plan_ready` (execution_steps: [step0 (priority 0), step1 (priority 1)])
3. **`execution_start`** (ExecutionProgressPage 생성)
4. **✅ `todo_updated` (step 0: "in_progress")** - 병렬 실행도 전송
5. **✅ `todo_updated` (step 1: "in_progress")** - 병렬 실행도 전송
6. `todo_updated` (step 0: "completed", step 1: "in_progress")
7. `todo_updated` (step 0: "completed", step 1: "completed")
8. `final_response`

**LLM 호출**: 최대 10회 (LLM #1~#6, #8~#11) - LLM #7은 선택적
**Memory**: 3-Tier 로드 + 저장 + 백그라운드 요약
**소요 시간**: ~15-20초

---

## 🎯 최적화 포인트 (v2.2 반영)

### ✅ 이미 적용된 최적화

1. **IRRELEVANT/UNCLEAR 조기 종료** (LLM #2 생략)
   - 위치: `planning_agent.py:172-181`
   - 효과: ~5초 → ~0.6초 (약 90% 단축)

2. **✨ 키워드 필터 (LLM #2 생략 확대)**
   - 위치: `planning_agent.py:314-341`
   - 대상: LEGAL_CONSULT, MARKET_INQUIRY 단순 질문
   - 효과: ~5초 → ~3초 (약 40% 단축)
   - 예시: "공인중개사 금지행위는?" → search_team만 (LLM #2 생략)

3. **✨ 3-Tier Hybrid Memory**
   - 위치: `simple_memory_service.py:394-509`
   - 전략: Short (전체 메시지) + Mid (요약) + Long (요약)
   - 토큰 절약: **93.0%** (8,424 → 591 tokens 실측)
   - 효과: LLM 컨텍스트 비용 대폭 절감 + 응답 품질 유지

4. **✨ 백그라운드 요약 (Fire-and-forget)**
   - 위치: `simple_memory_service.py:232-261`
   - 패턴: asyncio.create_task() + 독립 DB 세션
   - 효과: 메인 응답 속도 영향 없음 (비동기 처리)

5. **✨ Agent Priority 정렬**
   - 위치: `team_supervisor.py:177-189`
   - 수정: set() → sorted(key=priority)
   - 효과: step_0 (search) → step_1 (analysis) 순서 보장

6. **✨ 병렬 실행 Spinner 동작 (todo_updated 전송)**
   - 위치: `team_supervisor.py:421-515`
   - 수정: _execute_teams_parallel에 todo_updated 전송 추가
   - 효과: 복합 질문 진행 상황 실시간 표시

7. **WebSocket 실시간 통신**
   - HTTP POST (동기) → WebSocket (스트리밍)
   - 효과: 사용자 경험 개선, 진행 상황 실시간 확인

8. **Progress Flow UI** (v3)
   - ExecutionPlanPage + ExecutionProgressPage
   - 효과: 투명성 향상, 대기 시간 체감 감소

9. **Checkpointing (LangGraph + PostgreSQL)**
   - AsyncPostgresSaver 사용
   - 효과: 대화 상태 저장, 재연결 시 복구 가능

10. **Intent Analysis 파라미터 최적화**
    - Temperature: 0.1 → 0.0
    - max_tokens: 500 추가
    - 효과: ~0.5초 단축

11. **✨ Enum 직렬화 수정**
    - 위치: policy_matcher_tool.py, llm_service.py, ws_manager.py, team_supervisor.py
    - 수정: PolicyType.LOAN_SUPPORT → PolicyType.LOAN_SUPPORT.value
    - 효과: JSON/msgpack 직렬화 에러 완전 해결

### 💡 추가 최적화 가능

1. **패턴 기반 빠른 감지** (LLM #1도 생략)
   - 간단한 인사말은 LLM 호출 없이 즉시 판단
   - 예상 효과: 0.6초 → 0.1초

2. **병렬 LLM 호출**
   - LLM #4, #5, #6 동시 호출 (현재는 순차)
   - 예상 효과: ~30% 시간 단축

3. **캐싱 전략**
   - 동일 쿼리 재요청 시 결과 재사용
   - Redis/Memcached 활용

4. **Frontend Skeleton UI**
   - ExecutionPlanPage 대신 Skeleton 표시
   - 더 빠른 시각적 피드백

---

## 📂 주요 파일 구조 (v2.2 업데이트)

### Backend

```
backend/
├── app/
│   ├── api/
│   │   ├── chat_api.py               ✅ WebSocket 엔드포인트
│   │   │                             ✅ DELETE 세션 수정 (thread_id)
│   │   ├── ws_manager.py             ✅ ConnectionManager
│   │   │                             ✅ Enum 직렬화 수정
│   │   ├── session_manager.py        ✅ SessionManager (deprecated)
│   │   ├── postgres_session_manager.py ✅ PostgresSessionManager
│   │   │                             ✅ DELETE 세션 수정 (thread_id)
│   │   └── schemas.py
│   │
│   ├── core/
│   │   └── config.py                 ✅ 3-Tier Memory 설정 추가
│   │                                 - SHORTTERM_MEMORY_LIMIT: 5
│   │                                 - MIDTERM_MEMORY_LIMIT: 5
│   │                                 - LONGTERM_MEMORY_LIMIT: 10
│   │                                 - MEMORY_TOKEN_LIMIT: 2000
│   │                                 - MEMORY_MESSAGE_LIMIT: 10
│   │                                 - SUMMARY_MAX_LENGTH: 200
│   │
│   └── service_agent/
│       ├── supervisor/
│       │   └── team_supervisor.py    ✅ TeamBasedSupervisor (LangGraph)
│       │                             ✅ Memory 로딩 (planning_node)
│       │                             ✅ Memory 저장 (generate_response_node)
│       │                             ✅ Priority 정렬 (execute_teams_node)
│       │                             ✅ 병렬 실행 todo_updated 전송
│       │                             ✅ Enum 직렬화 수정
│       │
│       ├── cognitive_agents/
│       │   ├── planning_agent.py     ✅ PlanningAgent
│       │   │                         ✅ 키워드 필터 추가 (LEGAL_CONSULT/MARKET_INQUIRY)
│       │   └── query_decomposer.py   ✅ QueryDecomposer
│       │
│       ├── execution_agents/
│       │   ├── search_executor.py    ✅ SearchExecutor
│       │   ├── analysis_executor.py  ✅ AnalysisExecutor
│       │   └── document_executor.py  ✅ DocumentExecutor
│       │
│       ├── foundation/
│       │   ├── simple_memory_service.py ✅ SimpleMemoryService
│       │   │                            ✅ load_tiered_memories (3-Tier)
│       │   │                            ✅ summarize_with_llm (LLM #11)
│       │   │                            ✅ summarize_conversation_background
│       │   │                            ✅ save_conversation
│       │   │
│       │   ├── separated_states.py      ✅ ExecutionStepState
│       │   │                            ✅ priority: int 필드 추가
│       │   │
│       │   └── checkpointer.py          ✅ PostgreSQL checkpointer
│       │
│       ├── tools/
│       │   └── policy_matcher_tool.py   ✅ PolicyType.value 사용
│       │                                (Enum 직렬화 수정)
│       │
│       └── llm_manager/
│           ├── llm_service.py        ✅ LLMService
│           │                         ✅ Enum 직렬화 수정
│           ├── prompt_manager.py     ✅ PromptManager
│           └── prompts/
│               ├── cognitive/
│               │   ├── intent_analysis.txt
│               │   ├── agent_selection.txt
│               │   └── query_decomposition.txt
│               ├── execution/
│               │   ├── keyword_extraction.txt
│               │   ├── tool_selection_search.txt
│               │   ├── tool_selection_analysis.txt
│               │   ├── insight_generation.txt
│               │   └── response_synthesis.txt
│               └── common/
│                   └── conversation_summary.txt  ✅ v2.2 추가 (LLM #11)
```

### Frontend

```
frontend/
├── components/
│   ├── chat-interface.tsx            ✅ 메인 채팅 인터페이스
│   │                                 ✅ execution_start 처리
│   ├── execution-plan-page.tsx       ✅ 실행 계획 표시
│   ├── execution-progress-page.tsx   ✅ 실행 진행 상황 표시
│   │                                 ✅ Spinner 동작 (병렬 실행 포함)
│   ├── step-item.tsx                 ✅ 개별 Step UI
│   └── ui/
│       └── progress-bar.tsx          ✅ 진행률 바
│
├── hooks/
│   ├── use-chat-sessions.ts          ✅ 세션 CRUD
│   │                                 ✅ hard_delete=true
│   └── use-session.ts                ✅ 앱 레벨 세션
│
├── lib/
│   ├── ws.ts                         ✅ WebSocket 클라이언트
│   └── types.ts
│
└── types/
    ├── process.ts                    ✅ ProcessState 타입
    └── execution.ts                  ✅ ExecutionStep, ExecutionPlan 타입
```

### Database (PostgreSQL)

```sql
-- Checkpointing (LangGraph)
checkpoints (thread_id TEXT)          ✅ LangGraph 자동 생성
checkpoint_writes (thread_id TEXT)    ✅ LangGraph 자동 생성
checkpoint_blobs (thread_id TEXT)     ✅ LangGraph 자동 생성

-- Chat & Memory
chat_sessions (
  session_id VARCHAR(100),
  user_id INTEGER,
  session_metadata JSONB,             ✅ Memory 저장
  ...
)

chat_messages (
  session_id VARCHAR(100),
  role VARCHAR(20),
  content TEXT,
  ...
)

-- Note: thread_id = chat_session_id (값은 동일, 컬럼명만 다름)
```

---

## 🔮 향후 개선 계획 (v2.2 반영)

### Phase 1: 성능 최적화
- [x] ✅ 패턴 기반 키워드 필터 (LLM #2 생략 확대)
- [x] ✅ 3-Tier Hybrid Memory (토큰 93% 절감)
- [x] ✅ 백그라운드 요약 (Fire-and-forget)
- [ ] 패턴 기반 인사말 감지 (LLM #1도 생략)
- [ ] LLM 호출 병렬화 (LLM #4, #5, #6)
- [ ] 결과 캐싱 (Redis)

### Phase 2: 기능 확장
- [x] ✅ Agent Priority 정렬
- [x] ✅ 병렬 실행 Spinner 동작
- [ ] Human-in-the-Loop (Plan 수정)
- [ ] Step Skip 기능
- [ ] 재연결 시 State 복원 (Checkpointing 활용)

### Phase 3: UI/UX 개선
- [ ] Skeleton UI (로딩 상태)
- [ ] 애니메이션 추가 (전환 효과)
- [ ] 에러 처리 강화

### Phase 4: 모니터링
- [ ] LLM 호출 통계 대시보드
- [ ] 응답 시간 분석
- [ ] 에러 추적 (Sentry)
- [ ] Memory 사용 통계 (3-Tier 분포)

---

## 🐛 최근 수정 사항 (v2.2 패치)

### 1. Session Deletion 버그 수정 (251021_SESSION_DELETE_FIX.md)

**문제**: DELETE /api/v1/chat/sessions/xxx?hard_delete=true → 500 Error

**원인**:
```sql
-- 잘못된 쿼리
DELETE FROM checkpoints WHERE session_id = $1
-- ❌ checkpoints 테이블에는 session_id 컬럼이 없음

-- LangGraph는 thread_id 컬럼 사용
```

**해결**:
```python
# chat_api.py & postgres_session_manager.py
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
# thread_id(컬럼명) = session_id(값)
```

**테스트**: 4개 세션 연속 삭제 성공 ✅

---

### 2. Spinner 동작 개선 (251021_SPINNER_FIX.md)

**문제**: 복합 질문 입력 시 ExecutionProgressPage의 spinner가 작동하지 않음

**원인**: 병렬 실행 메서드(_execute_teams_parallel)에서 todo_updated 메시지 미전송

**해결**:
```python
# team_supervisor.py:421-515
async def _execute_teams_parallel(...):
    # ✅ 실행 전/후 todo_updated 전송 추가
    await progress_callback("todo_updated", {
        "execution_steps": planning_state["execution_steps"]
    })
```

**효과**: 복합 질문 진행 상황 실시간 표시 ✅

---

### 3. Agent Routing Priority 정렬 (251021_Agent Routing.md)

**문제**: step_1 (analysis) → step_0 (search) 역순 실행

**원인**: set() 사용으로 순서 손실

**해결**:
```python
# team_supervisor.py:177-189
# Before
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

# After
active_teams = []
seen_teams = set()

sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)
```

**효과**: search (priority 0) → analysis (priority 1) 순서 보장 ✅

---

### 4. Enum 직렬화 수정 (251020_ENUM_FIX.md)

**문제**: PolicyType Enum 객체가 JSON/msgpack 직렬화 불가

**원인**: Enum 객체를 직접 저장

**해결**:
```python
# policy_matcher_tool.py (11곳)
# Before
{"type": PolicyType.LOAN_SUPPORT}

# After
{"type": PolicyType.LOAN_SUPPORT.value}  # "대출지원"

# llm_service.py, ws_manager.py, team_supervisor.py (3곳)
def json_serial(obj):
    if isinstance(obj, Enum):
        return obj.value  # ✅ 추가
```

**효과**: JSON/msgpack 직렬화 100% 성공 ✅

---

## 📚 참고 문서

- **v2.2 패치노트**:
  - `reports/PatchNode/251021_Long-term_Memory.md` (3-Tier Memory)
  - `reports/PatchNode/251021_Agent Routing.md` (Priority 정렬)
  - `reports/PatchNode/251021_SPINNER_FIX.md` (병렬 실행 개선)
  - `reports/PatchNode/251021_SESSION_DELETE_FIX.md` (세션 삭제 수정)
  - `reports/PatchNode/251020_ENUM_FIX.md` (Enum 직렬화 수정)
  - `reports/PatchNode/251020_memory_phase1.md` (Memory 기본 구현)

- **아키텍처 문서**:
  - `reports/Manual/MEMORY_CONFIGURATION_GUIDE.md` (Memory 설정 가이드)
  - `reports/Manual/STATE_MANAGEMENT_GUIDE.md` (State 관리 가이드)
  - `backend/app/service_agent/reports/ARCHITECTURE_COMPLETE.md`

---

**생성일**: 2025-10-10
**버전**: 2.2
**마지막 업데이트**: 2025-10-22 (3-Tier Hybrid Memory, Agent Routing 개선, 버그 수정 4건 반영)
