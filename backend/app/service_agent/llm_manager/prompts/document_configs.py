"""
Python-based document prompt configurations.

단순하고 간결한 프롬프트 설정 관리.
- dataclass 기반 (무거운 의존성 없음)
- 필드 정의와 한글 라벨 관리
- IDE 자동완성 지원

Author: Holmes AI Team
Date: 2025-11-07
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PromptConfig:
    """
    프롬프트 설정 dataclass.

    Attributes:
        name: 프롬프트 식별자
        prompt_text: 프롬프트 템플릿 텍스트
        required_fields: 필수 필드 목록
        field_labels: 필드명 → 한글 라벨 매핑
        total_fields: 전체 필드 수
    """
    name: str
    prompt_text: str
    required_fields: List[str]
    field_labels: Dict[str, str]
    total_fields: int = 20


# ==================== 주택임대차 계약서 프롬프트 ====================

LEASE_CONTRACT_PROMPT_TEXT = """당신은 주택임대차 계약서 정보를 추출하는 전문가입니다.

사용자의 대화 내용과 이전 대화 기록에서 주택임대차 계약서 생성에 필요한 정보를 추출하세요.

## 추출해야 할 필드 (전체 20개 필드)

### 물건 정보
- address_road: 도로명주소 (예: "서울특별시 강남구 테헤란로 123")
- address_detail: 상세주소 (예: "456호 (101동 10층)")
- land_area: 토지 면적 (㎡) (선택)
- building_area: 건물 면적 (㎡) (선택)
- rental_area: 임차 면적 (㎡) (선택)

### 금액 정보
- deposit: 보증금 (숫자, 콤마 포함 가능, 예: "500,000,000")
- deposit_hangeul: 보증금 한글 (예: "오억") (선택)
- contract_payment: 계약금 (선택)
- monthly_rent: 월세 (선택, 전세인 경우 생략)
- monthly_rent_day: 월세 납부일 (매월 N일) (선택)
- management_fee: 관리비 (선택)

### 기간 정보
- start_date: 계약 시작일 (형식: "2024년 1월 1일")
- end_date: 계약 종료일 (형식: "2026년 1월 1일")

### 임대인 정보
- lessor_name: 임대인 성명
- lessor_address: 임대인 주소 (선택)
- lessor_phone: 임대인 전화번호 (선택)

### 임차인 정보
- lessee_name: 임차인 성명
- lessee_address: 임차인 주소 (선택)
- lessee_phone: 임차인 전화번호 (선택)

### 특약사항
- special_terms: 특약사항 (자유 기재) (선택)

## 추출 규칙

1. **날짜 형식 통일**: 모든 날짜는 "YYYY년 M월 D일" 형식으로 변환
   - 예: "2024-01-01" → "2024년 1월 1일"
   - 예: "내년 3월 1일" → "2026년 3월 1일" (현재 2025년 11월 기준)

2. **금액 형식 통일**: 모든 금액은 콤마로 구분된 숫자 문자열
   - 예: "오억" → "500,000,000"
   - 예: "5억" → "500,000,000"
   - 예: "1억5천만원" → "150,000,000"

3. **주소 정리**: 도로명주소만 추출 (지번주소 X)
   - address_road에는 도로명주소만
   - address_detail에는 동/층/호수 정보

4. **누락 필드**: 대화에서 언급되지 않은 필드는 null로 표시

5. **추론 금지**: 대화에 명시되지 않은 정보는 추측하지 말 것

## 응답 형식

반드시 JSON 형식으로 응답하세요. 모든 필드를 포함해야 합니다.

```json
{{
  "address_road": "서울특별시 강남구 테헤란로 123",
  "address_detail": "456호 (101동 10층)",
  "land_area": null,
  "building_area": null,
  "rental_area": "85",
  "deposit": "500,000,000",
  "deposit_hangeul": null,
  "contract_payment": null,
  "monthly_rent": null,
  "monthly_rent_day": null,
  "management_fee": null,
  "start_date": "2024년 1월 1일",
  "end_date": "2026년 1월 1일",
  "lessor_name": "홍길동",
  "lessor_address": null,
  "lessor_phone": null,
  "lessee_name": "김철수",
  "lessee_address": null,
  "lessee_phone": null,
  "special_terms": null
}}
```

## 사용자 대화 내용

{conversation_history}

{query}

## 지시사항

위 대화 내용에서 주택임대차 계약서 필드를 추출하여 JSON으로 응답하세요. 대화에서 언급되지 않은 필드는 null로 표시하세요.
"""

LEASE_CONTRACT_CONFIG = PromptConfig(
    name="lease_contract_extraction",
    prompt_text=LEASE_CONTRACT_PROMPT_TEXT,
    required_fields=[
        "address_road",
        "deposit",
        "start_date",
        "end_date",
        "lessor_name",
        "lessee_name"
    ],
    field_labels={
        # 물건 정보
        "address_road": "도로명주소",
        "address_detail": "상세주소",
        "land_area": "토지 면적",
        "building_area": "건물 면적",
        "rental_area": "임차 면적",
        # 금액 정보
        "deposit": "보증금",
        "deposit_hangeul": "보증금 (한글)",
        "contract_payment": "계약금",
        "monthly_rent": "월세",
        "monthly_rent_day": "월세 납부일",
        "management_fee": "관리비",
        # 기간 정보
        "start_date": "계약 시작일",
        "end_date": "계약 종료일",
        # 임대인 정보
        "lessor_name": "임대인 성명",
        "lessor_address": "임대인 주소",
        "lessor_phone": "임대인 전화번호",
        # 임차인 정보
        "lessee_name": "임차인 성명",
        "lessee_address": "임차인 주소",
        "lessee_phone": "임차인 전화번호",
        # 특약사항
        "special_terms": "특약사항"
    },
    total_fields=20
)


# ==================== Export ====================

DOCUMENT_PROMPTS: Dict[str, PromptConfig] = {
    "lease_contract_extraction": LEASE_CONTRACT_CONFIG,
    # 향후 추가할 문서 프롬프트들...
}


def get_prompt_config(prompt_name: str) -> PromptConfig:
    """
    Get prompt configuration by name.

    Args:
        prompt_name: Prompt identifier

    Returns:
        PromptConfig instance

    Raises:
        KeyError: If prompt not found
    """
    if prompt_name not in DOCUMENT_PROMPTS:
        available = ", ".join(DOCUMENT_PROMPTS.keys())
        raise KeyError(
            f"Prompt '{prompt_name}' not found. "
            f"Available: {available}"
        )

    return DOCUMENT_PROMPTS[prompt_name]
