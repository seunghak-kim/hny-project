# API 레퍼런스

**버전**: 1.0
**작성일**: 2025-10-14
**Base URL**: `http://localhost:8000` (개발 환경)

---

## 📚 목차

- [개요](#-개요)
- [인증](#-인증)
- [세션 관리 API](#-세션-관리-api)
- [WebSocket API](#-websocket-api)
- [에러 처리](#-에러-처리)
- [Rate Limiting](#-rate-limiting)
- [예제 코드](#-예제-코드)

---

## 🎯 개요

### API 구조

홈즈냥즈 API는 두 가지 통신 방식을 제공합니다:

| 방식 | 용도 | 프로토콜 |
|------|------|----------|
| **HTTP REST API** | 세션 관리 (생성, 조회, 삭제) | HTTP/1.1 |
| **WebSocket API** | 실시간 채팅 (질문/응답) | WebSocket |

### 엔드포인트 목록

#### HTTP REST API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/chat/start` | 새 세션 시작 |
| `GET` | `/api/v1/chat/{session_id}` | 세션 정보 조회 |
| `DELETE` | `/api/v1/chat/{session_id}` | 세션 삭제 |
| `GET` | `/api/v1/chat/stats/sessions` | 세션 통계 |
| `GET` | `/api/v1/chat/stats/websockets` | WebSocket 연결 통계 |
| `POST` | `/api/v1/chat/cleanup/sessions` | 만료된 세션 정리 |
| `GET` | `/health` | 헬스 체크 |
| `GET` | `/docs` | Swagger UI (API 문서) |

#### WebSocket API

| 경로 | 설명 |
|------|------|
| `ws://localhost:8000/api/v1/chat/ws/{session_id}` | 실시간 채팅 WebSocket |

---

## 🔐 인증

### 현재 상태 (v0.0.1)

- ❌ 인증 없음 (개발 환경)
- ⚠️ `session_id`만으로 접근 가능

### 향후 계획 (v1.0)

- ✅ JWT 기반 인증
- ✅ API Key 발급
- ✅ OAuth 2.0 지원

---

## 📡 세션 관리 API

### 1. 세션 시작

새로운 채팅 세션을 생성합니다.

#### Request

```http
POST /api/v1/chat/start
Content-Type: application/json

{
  "user_id": "user-123",  // Optional
  "metadata": {           // Optional
    "device": "mobile",
    "version": "1.0"
  }
}
```

#### Response (200 OK)

```json
{
  "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-10-14T14:30:00.000Z",
  "expires_at": "2025-10-15T14:30:00.000Z"
}
```

#### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_id` | string | ❌ | 사용자 ID (익명은 생략) |
| `metadata` | object | ❌ | 추가 세션 정보 |

#### curl 예시

```bash
curl -X POST http://localhost:8000/api/v1/chat/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### 2. 세션 정보 조회

기존 세션의 정보를 조회합니다.

#### Request

```http
GET /api/v1/chat/{session_id}
```

#### Response (200 OK)

```json
{
  "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-10-14T14:30:00.000Z",
  "expires_at": "2025-10-15T14:30:00.000Z",
  "last_activity": "2025-10-14T15:45:00.000Z",
  "metadata": {
    "user_id": "user-123"
  }
}
```

#### Response (404 Not Found)

```json
{
  "detail": "Session not found or expired: session-xxx"
}
```

#### curl 예시

```bash
curl -X GET http://localhost:8000/api/v1/chat/session-550e8400-e29b-41d4-a716-446655440000
```

---

### 3. 세션 삭제

세션을 삭제합니다 (로그아웃).

#### Request

```http
DELETE /api/v1/chat/{session_id}
```

#### Response (200 OK)

```json
{
  "message": "Session deleted successfully",
  "session_id": "session-550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response (404 Not Found)

```json
{
  "detail": "Session not found: session-xxx"
}
```

#### curl 예시

```bash
curl -X DELETE http://localhost:8000/api/v1/chat/session-550e8400-e29b-41d4-a716-446655440000
```

---

### 4. 세션 통계 조회

활성 세션 수를 조회합니다.

#### Request

```http
GET /api/v1/chat/stats/sessions
```

#### Response (200 OK)

```json
{
  "active_sessions": 42,
  "timestamp": "2025-10-14T14:30:00.000Z"
}
```

---

### 5. WebSocket 연결 통계 조회

활성 WebSocket 연결 수를 조회합니다.

#### Request

```http
GET /api/v1/chat/stats/websockets
```

#### Response (200 OK)

```json
{
  "active_connections": 15,
  "timestamp": "2025-10-14T14:30:00.000Z"
}
```

---

### 6. 만료된 세션 정리

만료된 세션을 수동으로 정리합니다.

#### Request

```http
POST /api/v1/chat/cleanup/sessions
```

#### Response (200 OK)

```json
{
  "cleaned_sessions": 28,
  "timestamp": "2025-10-14T14:30:00.000Z"
}
```

---

## 🔌 WebSocket API

### 연결

```javascript
const sessionId = "session-550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/${sessionId}`);
```

### 메시지 프로토콜

#### Client → Server

##### 1. 쿼리 전송

```json
{
  "type": "query",
  "query": "전세금 5% 인상 가능한가요?",
  "enable_checkpointing": true  // Optional, default: true
}
```

##### 2. Plan 승인/수정 (TODO)

```json
{
  "type": "interrupt_response",
  "action": "approve",  // "approve" or "modify"
  "modified_todos": []  // action이 "modify"일 때 수정된 todo 목록
}
```

##### 3. Todo 건너뛰기 (TODO)

```json
{
  "type": "todo_skip",
  "todo_id": "step_0"
}
```

---

#### Server → Client

##### 1. 연결 확인

```json
{
  "type": "connected",
  "session_id": "session-xxx",
  "timestamp": "2025-10-14T14:30:00.000Z"
}
```

##### 2. Planning 시작

```json
{
  "type": "planning_start",
  "message": "계획을 수립하고 있습니다...",
  "timestamp": "2025-10-14T14:30:01.000Z"
}
```

**Frontend 동작**: 스피너 표시

---

##### 3. Plan 준비 완료

```json
{
  "type": "plan_ready",
  "intent": "법률상담",
  "confidence": 0.95,
  "execution_steps": [
    {
      "step_id": "step_0",
      "step_type": "search",
      "agent_name": "search_team",
      "team": "search",
      "task": "법률 정보 검색",
      "description": "전세금 인상률 관련 법률 조항을 검색합니다",
      "status": "pending",
      "progress_percentage": 0,
      "started_at": null,
      "completed_at": null,
      "result": null,
      "error": null
    }
  ],
  "estimated_total_time": 7.5,
  "keywords": ["전세금", "인상", "법률"],
  "timestamp": "2025-10-14T14:30:02.000Z"
}
```

**Frontend 동작**:
1. ExecutionPlanPage 생성 (plan_ready 수신 즉시)
2. 800ms 후 ExecutionProgressPage로 자동 전환

---

##### 4. Todo 업데이트

```json
{
  "type": "todo_updated",
  "execution_steps": [
    {
      "step_id": "step_0",
      "step_type": "search",
      "agent_name": "search_team",
      "team": "search",
      "task": "법률 정보 검색",
      "description": "전세금 인상률 관련 법률 조항을 검색합니다",
      "status": "in_progress",  // ✅ 상태 변경
      "progress_percentage": 50,
      "started_at": "2025-10-14T14:30:03.000Z",
      "completed_at": null,
      "result": null,
      "error": null
    }
  ],
  "timestamp": "2025-10-14T14:30:03.000Z"
}
```

**Frontend 동작**: ExecutionProgressPage의 Step 상태 업데이트

---

##### 5. 최종 응답

```json
{
  "type": "final_response",
  "response": {
    "type": "summary",  // "summary" | "guidance" | "simple"
    "answer": "전세금 인상은 법률에 따라 5% 이내로 제한됩니다. 구체적으로 ...",
    "summary": "전세금 인상률은 주택임대차보호법에 따라 5% 이내로 제한됩니다.",
    "data": {
      "legal_results": [
        {
          "law_title": "주택임대차보호법",
          "article_number": "제7조의2",
          "content": "...",
          "relevance_score": 0.95
        }
      ],
      "trust_score": 0.92
    }
  },
  "timestamp": "2025-10-14T14:30:08.000Z"
}
```

**Frontend 동작**:
1. ExecutionProgressPage 제거
2. 답변 표시
3. idle 상태로 전환

---

##### 6. 에러

```json
{
  "type": "error",
  "error": "Query processing failed",
  "details": {
    "error": "Database connection timeout"
  },
  "timestamp": "2025-10-14T14:30:05.000Z"
}
```

**Frontend 동작**:
1. 에러 메시지 표시
2. idle 상태로 전환

---

### WebSocket 연결 상태

| 상태 | 설명 |
|------|------|
| `CONNECTING` (0) | 연결 시도 중 |
| `OPEN` (1) | 연결 성공 (메시지 전송 가능) |
| `CLOSING` (2) | 연결 종료 중 |
| `CLOSED` (3) | 연결 종료됨 |

### WebSocket 종료 코드

| 코드 | 설명 |
|------|------|
| 1000 | 정상 종료 |
| 1001 | 페이지 이탈 |
| 4004 | 세션 만료 또는 유효하지 않음 |

---

## ❌ 에러 처리

### 표준 에러 응답 (HTTP)

```json
{
  "detail": "Error message here"
}
```

### 에러 코드 (HTTP Status)

| 코드 | 설명 | 예시 |
|------|------|------|
| `400` | Bad Request | 잘못된 요청 형식 |
| `404` | Not Found | 세션을 찾을 수 없음 |
| `500` | Internal Server Error | 서버 내부 오류 |

### WebSocket 에러 메시지

```json
{
  "type": "error",
  "error": "Error message",
  "timestamp": "2025-10-14T14:30:00.000Z"
}
```

---

## ⏱️ Rate Limiting

### 현재 상태 (v0.0.1)

- ❌ Rate Limiting 없음

### 향후 계획 (v1.0)

| 항목 | 제한 |
|------|------|
| 세션 생성 | 10회/분 (IP당) |
| WebSocket 연결 | 5개 동시 연결 (세션당) |
| 쿼리 전송 | 10회/분 (세션당) |

---

## 💻 예제 코드

### Python (requests + websockets)

```python
import asyncio
import websockets
import requests
import json

# 1. 세션 생성
response = requests.post("http://localhost:8000/api/v1/chat/start", json={})
session_id = response.json()["session_id"]
print(f"Session created: {session_id}")

# 2. WebSocket 연결
async def chat():
    uri = f"ws://localhost:8000/api/v1/chat/ws/{session_id}"
    async with websockets.connect(uri) as websocket:
        # 연결 확인 메시지 수신
        msg = await websocket.recv()
        print("Connected:", json.loads(msg))

        # 쿼리 전송
        await websocket.send(json.dumps({
            "type": "query",
            "query": "전세금 5% 인상 가능한가요?"
        }))

        # 응답 수신 루프
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"[{data['type']}]")

            if data["type"] == "final_response":
                print("Answer:", data["response"]["answer"])
                break
            elif data["type"] == "error":
                print("Error:", data["error"])
                break

asyncio.run(chat())
```

---

### JavaScript (Fetch + WebSocket)

```javascript
// 1. 세션 생성
async function createSession() {
  const response = await fetch("http://localhost:8000/api/v1/chat/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
  const data = await response.json();
  return data.session_id;
}

// 2. WebSocket 연결
async function chat(sessionId) {
  const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/${sessionId}`);

  ws.onopen = () => {
    console.log("Connected");
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`[${data.type}]`, data);

    if (data.type === "connected") {
      // 쿼리 전송
      ws.send(JSON.stringify({
        type: "query",
        query: "전세금 5% 인상 가능한가요?"
      }));
    } else if (data.type === "plan_ready") {
      console.log("Execution steps:", data.execution_steps);
    } else if (data.type === "final_response") {
      console.log("Answer:", data.response.answer);
      ws.close();
    } else if (data.type === "error") {
      console.error("Error:", data.error);
      ws.close();
    }
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  ws.onclose = () => {
    console.log("Disconnected");
  };
}

// 실행
createSession().then(sessionId => {
  console.log("Session ID:", sessionId);
  chat(sessionId);
});
```

---

### TypeScript (React + WebSocket Hook)

```typescript
// lib/ws.ts
import { useEffect, useRef, useState } from "react";

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export function useWebSocket(sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as WebSocketMessage;
      setMessages((prev) => [...prev, data]);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.close();
    };
  }, [sessionId]);

  const sendQuery = (query: string) => {
    if (wsRef.current && isConnected) {
      wsRef.current.send(
        JSON.stringify({
          type: "query",
          query,
        })
      );
    }
  };

  return { messages, isConnected, sendQuery };
}
```

---

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [WebSocket MDN 문서](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [Swagger UI](http://localhost:8000/docs) (서버 실행 시)

---

**생성일**: 2025-10-14
**버전**: 1.0
**상태**: ✅ 프로덕션 준비 완료
