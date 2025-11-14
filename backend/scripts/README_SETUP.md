# HolmesNyangz 데이터베이스 설정 가이드

## 📋 실행 순서

### 1. 데이터베이스 초기화
```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# 기존 데이터 삭제
psql -U postgres -d real_estate -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"
```

### 2. 테이블 생성
```bash
# 모든 테이블 생성 (부동산 + 채팅)
uv run python scripts/init_db.py
```

### 3. 부동산 데이터 임포트
```bash
# 아파트/오피스텔
uv run python scripts/import_apt_ofst.py

# 원룸
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# 빌라
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### 4. 채팅 테이블 생성
```bash
# Checkpoint 테이블 생성
uv run python scripts/init_chat_tables.py
```

### 5. 더미 사용자 생성
```bash
# user_id=1 생성 (채팅 시스템용)
psql -U postgres -d real_estate -c "
INSERT INTO users (id, email, type, is_active, created_at)
VALUES (1, 'guest@holmesnyangz.com', 'USER', true, NOW())
ON CONFLICT (id) DO NOTHING;
"
```

---

## 📊 최종 결과

### 데이터베이스
- **부동산**: 9,738개
- **Regions**: 46개
- **Transactions**: 10,772개
- **채팅 테이블**: 준비 완료 (chat_sessions, chat_messages, checkpoints)

### 테이블 확인
```bash
psql -U postgres -d real_estate -c "
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
"
```

---

## ⚠️ 향후 수정 필요

### 1. ENUM 대소문자 불일치
**문제**: Python 코드는 소문자, DB는 대문자
- Python: `"user"`, `"admin"`, `"agent"`
- DB: `"USER"`, `"ADMIN"`, `"AGENT"`

**수정 필요 파일**: `backend/app/models/users.py`
```python
class UserType(enum.Enum):
    ADMIN = "ADMIN"  # "admin" → "ADMIN"
    USER = "USER"    # "user" → "USER"
    AGENT = "AGENT"  # "agent" → "AGENT"
```

### 2. Relationship 정리
**수정된 파일**:
- `backend/app/models/trust.py`: `back_populates` 제거
- `backend/app/models/users.py`: UserFavorite의 `back_populates` 제거

**원인**: RealEstate 모델에 해당 relationship이 없어서 발생한 에러 해결

---

## 🎯 완료 상태

✅ 데이터베이스 완전 초기화
✅ 부동산 데이터 임포트 완료
✅ 채팅 시스템 테이블 생성
✅ Session ID 형식: `session-{uuid}` 통일
✅ Frontend 코드 수정 완료 (loading 체크, activeSessionId 패턴)

**시스템 준비 완료! 테스트 가능!**
