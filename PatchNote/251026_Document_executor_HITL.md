# Patch Note: LangGraph 0.6 HITL (Human-in-the-Loop) 구현

**날짜**: 2025-10-26
**버전**: Beta v0.01 - HITL Release
**타입**: Major Feature Implementation
**작성자**: Development Team

---

## 📋 목차

1. [개요](#개요)
2. [주요 변경사항](#주요-변경사항)
3. [세부 구현 내용](#세부-구현-내용)
4. [파일별 변경사항](#파일별-변경사항)
5. [테스트 결과](#테스트-결과)
6. [알려진 이슈](#알려진-이슈)
7. [다음 단계](#다음-단계)

---

## 개요

### 구현 목적
LangGraph 0.6 공식 HITL 패턴을 사용하여 문서 생성 워크플로우에서 **사용자 승인 기능**을 구현했습니다. 사용자가 AI가 생성한 계약서 초안을 검토하고 승인/수정/거부할 수 있습니다.

### 핵심 기술 스택
- **LangGraph 0.6**: `interrupt()` 함수 및 `Command` API
- **AsyncPostgresSaver**: PostgreSQL 기반 checkpoint 저장
- **WebSocket**: 실시간 양방향 통신
- **React + TypeScript**: 프론트엔드 UI

### 구현 기간
2025-10-25 ~ 2025-10-26 (2일)

---

## 주요 변경사항

### ✨ 새로운 기능

#### 1. Document Team Workflow (HITL-enabled)
```
Planning → Search → Aggregate (⏸️ Interrupt) → Generate → Output
                       ↑
                   사용자 승인 대기
```

**핵심 노드**:
- **planning_node**: 문서 요구사항 분석
- **search_node**: 필요한 정보 수집
- **aggregate_node**: 결과 집계 + **interrupt() 호출**
- **generate_node**: 최종 문서 생성

#### 2. 프론트엔드 UI: lease_contract_page
**위치**: `frontend/components/lease_contract/lease_contract_page.tsx`

**기능**:
- 📄 집계된 내용 표시
- ✅ **승인** 버튼: 원본 그대로 최종 문서 생성
- ✏️ **수정** 버튼: Textarea 입력 → 수정사항 반영
- ❌ **거부** 버튼: 사용자가 문서 생성 거부 (현재: 참고용으로 생성)
- ✖️ **닫기** 버튼: 페이지 닫기

#### 3. WebSocket 프로토콜 확장
**새로운 메시지 타입**:
```typescript
// Backend → Frontend
{
  type: "workflow_interrupted",
  interrupted_by: "aggregate",
  interrupt_type: "approval",
  interrupt_data: {
    aggregated_content: string,
    search_results_count: number,
    message: string,
    options: {...}
  }
}

// Frontend → Backend
{
  type: "interrupt_response",
  action: "approve" | "modify" | "reject",
  feedback: string | null,
  modifications: string | null
}
```

---

## 세부 구현 내용

### 1. Backend: LangGraph HITL 패턴

#### 1.1 State Schema 확장
**파일**: `backend/app/service_agent/foundation/separated_states.py`

**추가된 필드**:
```python
class MainSupervisorState(TypedDict):
    # ... 기존 필드 ...

    # Document Team Fields
    planning_result: Optional[Dict[str, Any]]
    search_results: Optional[List[Dict[str, Any]]]
    aggregated_content: Optional[str]
    final_document: Optional[str]
    collaboration_result: Optional[Dict[str, Any]]  # HITL resume 값

    # HITL Fields
    workflow_status: Optional[str]  # "running", "interrupted", "completed", "cancelled"
    interrupted_by: Optional[str]   # "aggregate"
    interrupt_type: Optional[str]   # "approval"
    interrupt_data: Optional[Dict[str, Any]]
```

#### 1.2 Document Team Workflow 구현
**위치**: `backend/app/service_agent/teams/document_team/`

**파일 구조**:
```
document_team/
├── __init__.py          # build_document_workflow 노출
├── workflow.py          # StateGraph 구성
├── planning.py          # 문서 요구사항 분석
├── search.py            # 정보 수집
├── aggregate.py         # 결과 집계 + interrupt() ⭐
└── generate.py          # 최종 문서 생성
```

**workflow.py**: Linear Flow
```python
workflow = StateGraph(MainSupervisorState)

workflow.add_node("planning", planning_node)
workflow.add_node("search", search_node)
workflow.add_node("aggregate", aggregate_node)
workflow.add_node("generate", generate_node)

workflow.add_edge(START, "planning")
workflow.add_edge("planning", "search")
workflow.add_edge("search", "aggregate")
workflow.add_edge("aggregate", "generate")  # Resume 후 여기로
workflow.add_edge("generate", END)

compiled = workflow.compile(checkpointer=checkpointer)
```

#### 1.3 Interrupt 구현 (aggregate.py)
**핵심 코드**:
```python
from langgraph.types import interrupt  # ✅ LangGraph 0.6 공식 API

def aggregate_node(state: MainSupervisorState) -> Dict[str, Any]:
    aggregated_content = aggregate_results(state["search_results"])

    # Interrupt value에 metadata 포함
    interrupt_value = {
        "aggregated_content": aggregated_content,
        "search_results_count": len(search_results),
        "message": "Please review the aggregated content...",
        "options": {
            "approve": "Continue with document generation",
            "modify": "Provide feedback for modification",
            "reject": "Cancel document generation"
        },
        "_metadata": {
            "interrupted_by": "aggregate",
            "interrupt_type": "approval",
            "node_name": "document_team.aggregate"
        }
    }

    # ⏸️ Workflow 중단, 사용자 입력 대기
    user_feedback = interrupt(interrupt_value)

    # 🔄 여기서 재개됨 (Command(resume=...) 호출 시)
    if user_feedback.get("action") == "modify":
        aggregated_content = apply_user_feedback(aggregated_content, user_feedback)

    return {
        "aggregated_content": aggregated_content,
        "collaboration_result": user_feedback,
        "workflow_status": "running"
    }
```

**동작 원리**:
1. `interrupt(value)` 호출 → workflow 중단, value는 checkpoint에 저장
2. Backend는 `get_state()` API로 interrupt 감지
3. Frontend에 `workflow_interrupted` 메시지 전송
4. 사용자 응답 → Backend는 `Command(resume=user_feedback)` 호출
5. `interrupt()`가 `user_feedback`를 반환하며 재개

#### 1.4 Resume 구현 (chat_api.py)
**Interrupt 감지**:
```python
async def _process_query_async(...):
    result = await supervisor.app.ainvoke(initial_state, config=config)

    workflow_status = result.get("workflow_status")

    if workflow_status == "interrupted":
        state_snapshot = await supervisor.app.aget_state(config)

        # ✅ interrupt value는 tasks[0].interrupts[0]에 저장됨
        if state_snapshot.tasks and len(state_snapshot.tasks) > 0:
            first_task = state_snapshot.tasks[0]

            if hasattr(first_task, 'interrupts') and first_task.interrupts:
                interrupt_value = first_task.interrupts[0].value

                # metadata 추출
                interrupt_data = interrupt_value.copy()
                metadata = interrupt_data.pop("_metadata", {})
                interrupted_by = metadata.get("interrupted_by", "unknown")
                interrupt_type = metadata.get("interrupt_type", "approval")

        # WebSocket으로 알림 전송
        await conn_mgr.send_message(session_id, {
            "type": "workflow_interrupted",
            "interrupted_by": interrupted_by,
            "interrupt_type": interrupt_type,
            "interrupt_data": interrupt_data,
            "message": "워크플로우가 사용자 승인을 기다리고 있습니다."
        })

        # 세션 저장 (resume 시 사용)
        _interrupted_sessions[session_id] = {
            "config": config,
            "timestamp": datetime.now()
        }
```

**Resume 처리**:
```python
async def _resume_workflow_async(...):
    from langgraph.types import Command

    # ✅ Command를 첫 번째 positional parameter로 전달
    result = await supervisor.app.ainvoke(
        Command(resume=user_feedback),  # ← 여기로 전달됨
        config=config
    )

    # final_response 추출 및 전송
    final_response = result.get("final_response") if result else None
    if final_response is None:
        final_response = {}

    await conn_mgr.send_message(session_id, {
        "type": "final_response",
        "response": final_response,
        "resumed": True
    })
```

#### 1.5 Document Team → Parent Graph 연동
**문제**: Resume 후 Parent Graph가 Document Team 결과를 인식하지 못함

**해결**: `generate_node`에서 `team_results` 추가 (generate.py)
```python
def generate_node(state: MainSupervisorState) -> Dict[str, Any]:
    final_document = format_document(...)

    final_response = {
        "answer": final_document,
        "document_type": doc_type,
        "user_approved": user_action == "approve",
        "user_action": user_action,
        "type": "document"
    }

    # ✅ Parent Graph aggregation을 위해 team_results 추가
    team_results = {
        "document": {
            "status": "success",
            "data": final_response
        }
    }

    return {
        "final_document": final_document,
        "final_response": final_response,
        "workflow_status": "completed",
        "team_results": team_results  # ✅ 추가
    }
```

#### 1.6 통계 로그 수정 (team_supervisor.py)
**문제**: Document Team이 `execute_teams_node`를 거치지 않아 `completed_teams` 리스트에 추가되지 않음
**증상**: `Aggregation complete: 0/1 teams succeeded` (실제로는 1개 성공)

**해결**: `aggregated_results` 기반 카운팅
```python
async def aggregate_results_node(self, state: MainSupervisorState):
    # ... aggregation logic ...

    # ✅ 실제 데이터 기반으로 통계 계산
    total_teams = len(state.get("active_teams", []))
    succeeded_teams = len([
        name for name, data in aggregated.items()
        if data.get("status") == "success"
    ])
    failed_teams = len([
        name for name, data in aggregated.items()
        if data.get("status") == "failed"
    ])

    logger.info(f"=== Aggregation complete: {succeeded_teams}/{total_teams} teams succeeded, {failed_teams} failed ===")
```

**결과**: `Aggregation complete: 1/1 teams succeeded, 0 failed` ✅

#### 1.7 Parent Graph에 Document Team 통합 (team_supervisor.py)
```python
from app.service_agent.teams.document_team import build_document_workflow

def _build_graph_with_checkpointer(self):
    workflow = StateGraph(MainSupervisorState)

    # ✅ Document Team을 compiled subgraph로 추가
    document_workflow = build_document_workflow(checkpointer=self.checkpointer)

    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("execute_teams", self.execute_teams_node)
    workflow.add_node("document_team", document_workflow)  # ✅ Subgraph
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # Routing
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning_with_hitl,
        {
            "document": "document_team",  # ✅ HITL-enabled
            "execute": "execute_teams",
            "respond": "generate_response"
        }
    )

    workflow.add_edge("document_team", "aggregate")
    workflow.add_edge("execute_teams", "aggregate")
    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)

    self.app = workflow.compile(checkpointer=self.checkpointer)
```

#### 1.8 Windows 호환성 (main.py)
```python
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.info("✅ Windows Compatibility: Set WindowsSelectorEventLoopPolicy for AsyncPostgresSaver")
```

---

### 2. Frontend: UI 구현

#### 2.1 lease_contract_page.tsx
**위치**: `frontend/components/lease_contract/lease_contract_page.tsx`

**인터페이스**:
```typescript
interface LeaseContractPageProps {
  interruptData?: {
    aggregated_content?: string
    search_results_count?: number
    message?: string
    options?: {
      approve: string
      modify: string
      reject: string
    }
  }
  onApprove: () => void
  onModify: (modifications: string) => void
  onReject: () => void
  onClose: () => void
}
```

**핵심 기능**:
```typescript
export function LeaseContractPage({ interruptData, onApprove, onModify, onReject, onClose }) {
  const [showModifyInput, setShowModifyInput] = useState(false)
  const [modifications, setModifications] = useState("")

  const handleApprove = () => {
    onApprove()
    onClose()
  }

  const handleModify = () => {
    if (!showModifyInput) {
      setShowModifyInput(true)  // Textarea 표시
      return
    }

    if (modifications.trim()) {
      onModify(modifications)  // 수정사항 제출
      onClose()
    }
  }

  const handleReject = () => {
    onReject()
    onClose()
  }

  // ... UI rendering ...
}
```

#### 2.2 chat-interface.tsx 통합
**WebSocket 메시지 처리**:
```typescript
const handleWSMessage = (message: any) => {
  switch (message.type) {
    case 'workflow_interrupted':
      setLeaseContractData({
        interrupt_data: message.interrupt_data,
        interrupted_by: message.interrupted_by,
        interrupt_type: message.interrupt_type,
        message: message.message
      })
      setShowLeaseContract(true)
      break

    case 'final_response':
      setShowLeaseContract(false)
      // ... 응답 처리 ...
      break
  }
}
```

**Resume 요청 전송**:
```typescript
<LeaseContractPage
  interruptData={leaseContractData?.interrupt_data}

  onApprove={() => {
    wsClientRef.current.send({
      type: "interrupt_response",
      action: "approve",
      feedback: null
    })
  }}

  onModify={(modifications: string) => {
    wsClientRef.current.send({
      type: "interrupt_response",
      action: "modify",
      feedback: modifications,
      modifications: modifications
    })
  }}

  onReject={() => {
    wsClientRef.current.send({
      type: "interrupt_response",
      action: "reject",
      feedback: null
    })
  }}

  onClose={() => {
    setShowLeaseContract(false)
    setLeaseContractData(null)
  }}
/>
```

---

## 파일별 변경사항

### Backend

| 파일 | 변경 타입 | 주요 변경 내용 |
|------|----------|----------------|
| `app/service_agent/foundation/separated_states.py` | Modified | HITL 관련 필드 추가 (planning_result, search_results, aggregated_content, final_document, collaboration_result, workflow_status, interrupted_by, interrupt_type, interrupt_data) |
| `app/service_agent/teams/document_team/__init__.py` | **New** | build_document_workflow 노출 |
| `app/service_agent/teams/document_team/workflow.py` | **New** | Document Team StateGraph 구성 |
| `app/service_agent/teams/document_team/planning.py` | **New** | 문서 요구사항 분석 노드 |
| `app/service_agent/teams/document_team/search.py` | **New** | 정보 수집 노드 (Mock 데이터) |
| `app/service_agent/teams/document_team/aggregate.py` | **New** | 결과 집계 + interrupt() 호출 |
| `app/service_agent/teams/document_team/generate.py` | **New** | 최종 문서 생성 + team_results 추가 |
| `app/service_agent/supervisor/team_supervisor.py` | Modified | Document Team 통합, _route_after_planning_with_hitl() 추가, aggregate_results_node 통계 로직 수정 |
| `app/api/chat_api.py` | Modified | Interrupt 감지 로직, _resume_workflow_async() 추가, interrupt_response 메시지 핸들러 추가, _interrupted_sessions 딕셔너리 추가 |
| `app/main.py` | Modified | Windows EventLoopPolicy 설정 |

### Frontend

| 파일 | 변경 타입 | 주요 변경 내용 |
|------|----------|----------------|
| `components/lease_contract/lease_contract_page.tsx` | **New** | HITL UI 페이지 전체 구현 (승인/수정/거부 버튼, Textarea) |
| `components/chat-interface.tsx` | Modified | LeaseContractPage 통합, workflow_interrupted 핸들러, interrupt_response 전송 로직 |

### Documentation

| 파일 | 변경 타입 | 주요 변경 내용 |
|------|----------|----------------|
| `reports/human_in_the_loop/COMMAND_API_USAGE_251026.md` | **New** | LangGraph Command API 조사 및 코드 분석 문서 |
| `reports/PatchNote/251026_LANGGRAPH_HITL_IMPLEMENTATION.md` | **New** | 본 패치노트 |

---

## 테스트 결과

### 테스트 환경
- **Backend**: Windows 11, Python 3.11, uvicorn
- **Frontend**: Next.js (localhost:3000)
- **Database**: PostgreSQL 16
- **LangGraph**: 0.6.x

### 테스트 시나리오 및 결과

#### ✅ Test 1: 승인 (Approve)
**입력**: "임대차 계약서 작성해줘" → Interrupt → "승인" 버튼

**백엔드 로그**:
```
⏸️  Requesting human approval via interrupt()
📥 Interrupt response received: approve
🔄 Resuming workflow for session-xxx
📊 Aggregate node: Consolidating search results (재시작)
▶️  Workflow resumed with user feedback
User feedback: {'action': 'approve', 'feedback': None, ...}
📝 Generate node: Creating final document
Document generation complete: 354 characters
✅ Final response created: type=general, action=approve
✅ Document Team results added to team_results
[TeamSupervisor] === Aggregation complete: 1/1 teams succeeded, 0 failed ===
[TeamSupervisor] Response type: answer
✅ Workflow resumed successfully
```

**결과**: ✅ 성공 - 원본 그대로 최종 문서 생성

---

#### ✅ Test 2: 수정 (Modify)
**입력**: "임대차 계약서 작성해줘" → Interrupt → "수정" 버튼 → "임대료를 100만원 올려주세요" 입력 → "수정 제출"

**백엔드 로그**:
```
📥 Interrupt response received: modify
User feedback: {'action': 'modify', 'modifications': '임대료를 100만원 올려주세요', ...}
Content modified based on user feedback
Document generation complete: 397 characters  ← 43자 증가 (수정사항 추가됨)
✅ Final response created: type=general, action=modify
```

**생성된 문서**:
```
Aggregated Content:
- 임대차: Mock search result for: 임대차
- 계약서: Mock search result for: 계약서
- 작성해줘: Mock search result for: 작성해줘

[User Feedback Applied]  ← 추가됨
임대료를 100만원 올려주세요
```

**결과**: ✅ 성공 - 수정사항이 반영된 문서 생성

---

#### ✅ Test 3: 거부 (Reject)
**입력**: "임대차 계약서 작성해줘" → Interrupt → "거부" 버튼

**백엔드 로그**:
```
📥 Interrupt response received: reject
User feedback: {'action': 'reject', 'feedback': None, ...}
📝 Generate node: Creating final document
Document generation complete: 355 characters
✅ Final response created: type=general, action=reject
```

**결과**: ✅ 성공 - 문서 생성됨 (metadata에 user_action: "reject" 표시)

**참고**: 현재 거부 시에도 참고용으로 문서는 생성됩니다. 향후 비즈니스 요구사항에 따라 생성 중단 로직 추가 가능.

---

### 성능 메트릭

| 시나리오 | 총 실행 시간 | LLM 호출 | 토큰 사용 |
|---------|-------------|---------|----------|
| 승인 | 17.32s | 3회 | ~4,900 |
| 수정 | 34.74s | 3회 | ~5,200 |
| 거부 | 48.65s | 3회 | ~5,100 |

**LLM 호출 내역**:
1. intent_analysis: ~3,000 토큰
2. agent_selection: ~2,500 토큰
3. response_synthesis: ~1,400 토큰

---

## 알려진 이슈

### 1. 거부(Reject) 동작 명확화 필요 ⚠️
**현상**: 거부 버튼 클릭 시에도 문서가 생성됨 (metadata에 `user_action: "reject"` 표시만 됨)

**원인**: 현재 구현은 거부 시에도 workflow를 계속 진행하도록 설계됨

**영향**: 낮음 (기능적으로는 작동하지만 비즈니스 의도와 다를 수 있음)

**해결 옵션**:
- **Option A**: 현재 유지 (참고용으로 문서 생성)
- **Option B**: 거부 시 생성 중단, 안내 메시지만 표시
  ```python
  # aggregate.py에서
  if user_feedback.get("action") == "reject":
      return {
          "workflow_status": "cancelled",
          "final_response": {
              "type": "info",
              "answer": "문서 생성이 사용자에 의해 취소되었습니다."
          }
      }
  ```

**권장**: 비즈니스 요구사항 확인 후 결정

---

### 2. Node 재실행 (의도된 동작)
**현상**: Resume 시 aggregate_node가 처음부터 다시 실행됨

**원인**: LangGraph 0.6 공식 동작 - "Graph execution starts from the **beginning of the graph node** where the last interrupt was triggered."

**영향**: 낮음 (aggregation은 idempotent하므로 기능적 문제 없음, 약간의 성능 오버헤드만 존재)

**로그 예시**:
```
📊 Aggregate node: Consolidating search results (첫 실행)
⏸️  Requesting human approval
[사용자 승인]
📊 Aggregate node: Consolidating search results (재시작) ← 정상
⏸️  Requesting human approval (재도달)
▶️  Workflow resumed ← resume 값 받음
```

**최적화 방안** (필요 시):
```python
# aggregate_node에서 캐싱
if state.get("_aggregated_cache"):
    aggregated_content = state["_aggregated_cache"]
else:
    aggregated_content = aggregate_results(search_results)
    state["_aggregated_cache"] = aggregated_content
```

---

### 3. Mock 데이터 사용 중
**현상**: `search_node`가 실제 검색 대신 Mock 데이터 반환

**영향**: 중간 (프로토타입으로는 충분하지만 실제 서비스에는 부적합)

**해결**: 실제 SearchTeam 또는 RAG 연동 필요

---

## 다음 단계

### Phase 1: 기능 개선 (우선순위: 높음)

#### 1.1 거부 동작 명확화
- [ ] 비즈니스 요구사항 확인
- [ ] 필요 시 거부 시 생성 중단 로직 추가
- [ ] Conditional edge 추가 (`aggregate` → `generate` or `END`)

#### 1.2 실제 데이터 통합
- [ ] Mock 데이터를 실제 SearchTeam 결과로 대체
- [ ] RAG (Retrieval-Augmented Generation) 연동
- [ ] 계약서 템플릿 DB 구축

#### 1.3 문서 포맷 개선
- [ ] `lease_contract_template_with_placeholders.docx` 연동
- [ ] LLM으로 템플릿 자동 채우기
- [ ] PDF 생성 기능

---

### Phase 2: UX 개선 (우선순위: 중간)

#### 2.1 UI/UX 향상
- [ ] lease_contract_page 디자인 개선
- [ ] 수정사항 미리보기 기능
- [ ] 변경 사항 하이라이트
- [ ] Loading indicator 추가

#### 2.2 에러 처리 강화
- [ ] Resume timeout 처리 (예: 10분 후 자동 취소)
- [ ] Invalid feedback 검증
- [ ] Session 만료 처리
- [ ] 재시도 메커니즘

---

### Phase 3: 성능 최적화 (우선순위: 낮음)

#### 3.1 Node 재실행 최적화
- [ ] Aggregation 결과 캐싱
- [ ] 불필요한 재계산 방지

#### 3.2 응답 속도 개선
- [ ] LLM 호출 병렬화 (가능한 경우)
- [ ] 응답 스트리밍 (Streaming response)
- [ ] Checkpoint 압축

---

### Phase 4: 확장성 (우선순위: 낮음)

#### 4.1 Multiple Interrupts 지원
- [ ] 여러 단계에서 승인 대기 (예: Planning → Search → Aggregate → Generate)
- [ ] Index 기반 resume 값 관리

#### 4.2 다른 팀에 HITL 적용
- [ ] SearchTeam: 검색 전략 승인
- [ ] AnalysisTeam: 분석 결과 검증

---

## 참고 자료

### 공식 문서
- [LangGraph HITL Overview](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [Wait for User Input](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
- [LangGraph Command API](https://langchain-ai.github.io/langgraph/reference/types/)
- [Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts)

### 내부 문서
- `reports/human_in_the_loop/COMMAND_API_USAGE_251026.md` - Command API 조사 및 분석
- `reports/BACKUP_HITL_251025/START_HERE.md` - 초기 구현 계획

### 주요 파일
**Backend**:
- `backend/app/service_agent/teams/document_team/aggregate.py` - interrupt() 호출
- `backend/app/service_agent/teams/document_team/generate.py` - final_response 생성
- `backend/app/api/chat_api.py` - Interrupt 감지 및 Resume

**Frontend**:
- `frontend/components/lease_contract/lease_contract_page.tsx` - HITL UI
- `frontend/components/chat-interface.tsx` - WebSocket 통합

---

## 팀 노트

### 성공 요인
1. ✅ LangGraph 0.6 공식 패턴 철저히 준수
2. ✅ Command API를 첫 번째 positional parameter로 전달 (핵심!)
3. ✅ Interrupt value를 tasks[0].interrupts[0]에서 추출 (공식 위치)
4. ✅ team_results로 Parent Graph 연동
5. ✅ 통계 로그를 실제 데이터 기반으로 수정

### 주요 실수 및 교훈
1. ❌ 초기에 Command를 keyword argument로 전달 → 공식 문서 재확인 필요
2. ❌ state.values에서 interrupt 데이터 찾으려 함 → tasks에 있음
3. ❌ completed_teams로 통계 계산 → aggregated_results 사용해야 함
4. ✅ 각 수정마다 로그 확인하여 빠르게 문제 해결

### 개발 시간
- 구현: 12시간
- 디버깅: 4시간
- 테스트: 2시간
- 문서화: 2시간
- **총 시간**: 20시간

---

**End of Patch Note**

**작성**: 2025-10-26
**검토**: Pending
**승인**: Pending
