"""
은행별 대출 상품 비교 및 조건 분석 Tool
여러 은행의 대출 조건, 금리, 한도를 비교하여 최적의 대출 상품 추천
PostgreSQL 기반
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


class LoanComparisonTool:
    """
    은행별 대출 상품 비교 도구
    여러 은행의 대출 조건을 비교하고 사용자 조건에 맞는 최적 상품 추천
    """

    def __init__(self, loan_search_tool=None):
        """
        초기화

        Args:
            loan_search_tool: 대출 상품 검색 도구 (선택적)
        """
        from app.db.postgre_db import SessionLocal

        self.SessionLocal = SessionLocal
        self.loan_search_tool = loan_search_tool
        self.name = "loan_comparison"

        # MongoDB 컬렉션 정보 (sinhan과 shinhan 모두 지원)
        self.bank_collections = ['kb', 'hana', 'shinhan', 'sinhan', 'woori', 'kakao', 'sc', 'k']

        # 은행 이름 매핑 (한글 → 영문 컬렉션명)
        # MongoDB에 따라 sinhan 또는 shinhan 사용 가능
        self.bank_name_mapping = {
            '케이뱅크': 'k',
            'k뱅크': 'k',
            'KB': 'kb',
            'kb': 'kb',
            'kb국민은행': 'kb',
            'KB국민은행': 'kb',
            '국민은행': 'kb',
            '하나': 'hana',
            '하나은행': 'hana',
            '신한': 'shinhan',  # 기본값은 shinhan
            '신한은행': 'shinhan',
            '우리': 'woori',
            '우리은행': 'woori',
            '카카오': 'kakao',
            '카카오뱅크': 'kakao',
            'SC': 'sc',
            'sc': 'sc',
            'SC제일': 'sc',
            'SC제일은행': 'sc',
            'sc제일은행': 'sc'
        }

        # 은행 표시 이름 (영문 컬렉션명 → 한글)
        self.bank_display_names = {
            'k': 'k뱅크',
            'kb': 'kb국민은행',
            'hana': '하나은행',
            'shinhan': '신한은행',
            'sinhan': '신한은행',  # 별칭
            'woori': '우리은행',
            'kakao': '카카오뱅크',
            'sc': 'sc제일은행'
        }

        # 대출 유형 별칭 매핑 (유사한 대출 상품명 매핑)
        self.loan_type_aliases = {
            '주택담보대출': ['주택담보대출', '아파트담보대출', '주택담보', '아파트담보', '담보대출'],
            '전세자금대출': ['전세자금대출', '전세대출', '전월세대출', '전월세보증금'],
            '신용대출': ['신용대출', '마이너스통장', '신용'],
            '주택구입자금대출': ['주택구입자금대출', '주택구입', '주택담보대출']
        }

        # 하드코딩된 은행별 대출 상품 데이터는 백업용으로만 사용
        # MongoDB 조회 실패시에만 사용됨
        self.bank_products_fallback = {
            "KB국민은행": {
                "주택담보대출": {
                    "금리_범위": {"min": 3.5, "max": 5.2},
                    "최대_한도": 10_000_000_000,  # 100억
                    "LTV_최대": 0.7,
                    "우대금리": ["급여이체 -0.3%", "자동이체 -0.1%", "KB카드 사용 -0.2%"],
                    "특징": ["고액 자산가 우대", "장기 고정금리 가능"],
                },
                "전세자금대출": {
                    "금리_범위": {"min": 3.2, "max": 4.8},
                    "최대_한도": 3_000_000_000,
                    "우대금리": ["청년 -0.5%", "신혼부부 -0.4%"],
                    "특징": ["보증금 80% 한도", "중도상환 수수료 면제"],
                },
            },
            "신한은행": {
                "주택담보대출": {
                    "금리_범위": {"min": 3.4, "max": 5.0},
                    "최대_한도": 10_000_000_000,
                    "LTV_최대": 0.7,
                    "우대금리": ["급여이체 -0.4%", "신한카드 -0.2%", "S20 뱅킹 -0.1%"],
                    "특징": ["디지털 특화 우대", "온라인 신청 가능"],
                },
                "전세자금대출": {
                    "금리_범위": {"min": 3.1, "max": 4.7},
                    "최대_한도": 3_000_000_000,
                    "우대금리": ["청년 -0.6%", "신혼부부 -0.5%"],
                    "특징": ["온라인 즉시 심사", "빠른 승인"],
                },
            },
            "우리은행": {
                "주택담보대출": {
                    "금리_범위": {"min": 3.6, "max": 5.3},
                    "최대_한도": 10_000_000_000,
                    "LTV_최대": 0.7,
                    "우대금리": ["급여이체 -0.35%", "우리카드 -0.15%", "예적금 -0.2%"],
                    "특징": ["장기 거래 고객 우대", "안정적 금리"],
                },
                "전세자금대출": {
                    "금리_범위": {"min": 3.3, "max": 4.9},
                    "최대_한도": 3_000_000_000,
                    "우대금리": ["청년 -0.45%", "신혼부부 -0.4%"],
                    "특징": ["전세보증보험 연계", "안정적 운영"],
                },
            },
            "하나은행": {
                "주택담보대출": {
                    "금리_범위": {"min": 3.5, "max": 5.1},
                    "최대_한도": 10_000_000_000,
                    "LTV_최대": 0.7,
                    "우대금리": ["급여이체 -0.3%", "하나카드 -0.2%", "하나머니 -0.15%"],
                    "특징": ["외국인 대출 특화", "다양한 상환 방식"],
                },
                "전세자금대출": {
                    "금리_범위": {"min": 3.2, "max": 4.8},
                    "최대_한도": 3_000_000_000,
                    "우대금리": ["청년 -0.5%", "신혼부부 -0.45%"],
                    "특징": ["유연한 상환 조건", "중도상환 우대"],
                },
            },
            "NH농협은행": {
                "주택담보대출": {
                    "금리_범위": {"min": 3.4, "max": 5.0},
                    "최대_한도": 10_000_000_000,
                    "LTV_최대": 0.7,
                    "우대금리": ["급여이체 -0.4%", "NH카드 -0.25%", "조합원 -0.3%"],
                    "특징": ["농협 조합원 우대", "지역 밀착형"],
                },
                "전세자금대출": {
                    "금리_범위": {"min": 3.0, "max": 4.6},
                    "최대_한도": 3_000_000_000,
                    "우대금리": ["청년 -0.6%", "신혼부부 -0.5%", "조합원 -0.3%"],
                    "특징": ["조합원 특화 상품", "낮은 금리"],
                },
            },
        }

        # 정책금융 상품
        self.policy_loans = {
            "주택금융공사_보금자리론": {
                "금리_범위": {"min": 3.2, "max": 4.5},
                "최대_한도": 6_000_000_000,
                "LTV_최대": 0.7,
                "대상": "무주택자 또는 1주택자",
                "특징": ["고정금리/변동금리 선택", "서민 중산층 지원"],
            },
            "주택금융공사_디딤돌대출": {
                "금리_범위": {"min": 2.15, "max": 3.0},
                "최대_한도": 3_600_000_000,
                "LTV_최대": 0.7,
                "대상": "생애최초 무주택자",
                "특징": ["초저금리", "소득별 차등 금리"],
            },
            "주택금융공사_적격대출": {
                "금리_범위": {"min": 3.8, "max": 5.2},
                "최대_한도": 9_000_000_000,
                "LTV_최대": 0.7,
                "대상": "6억원 이하 주택 구입자",
                "특징": ["장기 고정금리", "안정적 상환"],
            },
        }

        logger.info(f"LoanComparisonTool initialized with PostgreSQL (banks: {', '.join(self.bank_collections)})")

    def _normalize_bank_names(self, banks: Optional[List[str]]) -> List[str]:
        """
        사용자 입력 은행명을 컬렉션명으로 변환하고 실제로 존재하는지 확인

        Args:
            banks: 사용자가 입력한 은행 리스트 (None이면 모든 은행)

        Returns:
            실제로 존재하는 컬렉션명 리스트
        """
        if banks is None:
            # 모든 은행 중 실제로 존재하는 것만 반환
            return self._filter_existing_collections(self.bank_collections)

        normalized = []
        for bank_input in banks:
            bank_lower = bank_input.lower()

            # 매핑 테이블에서 찾기
            if bank_input in self.bank_name_mapping:
                collection_name = self.bank_name_mapping[bank_input]
                if collection_name not in normalized:
                    normalized.append(collection_name)
            # 이미 컬렉션명인 경우
            elif bank_lower in self.bank_collections:
                if bank_lower not in normalized:
                    normalized.append(bank_lower)
            # 부분 매칭 시도
            else:
                matched = False
                for korean_name, collection_name in self.bank_name_mapping.items():
                    if bank_input in korean_name or korean_name in bank_input:
                        if collection_name not in normalized:
                            normalized.append(collection_name)
                            matched = True
                            break
                if not matched:
                    logger.warning(f"Bank not found in mapping: {bank_input}")

        # 실제로 존재하는 컬렉션만 필터링
        existing = self._filter_existing_collections(normalized)
        return existing if existing else self._filter_existing_collections(self.bank_collections)

    def _filter_existing_collections(self, bank_names: List[str]) -> List[str]:
        """
        실제로 PostgreSQL에 존재하는 은행만 필터링

        Args:
            bank_names: 확인할 은행명 리스트

        Returns:
            실제로 존재하는 은행명 리스트
        """
        existing = []
        db = self.SessionLocal()

        try:
            for name in bank_names:
                display_name = self.bank_display_names.get(name, name)

                # PostgreSQL에서 해당 은행의 상품이 있는지 확인
                query = """
                    SELECT COUNT(*)
                    FROM products p
                    JOIN banks b ON p.bank_id = b.id
                    WHERE b.bank_name ILIKE :bank_name
                """
                result = db.execute(text(query), {'bank_name': f'%{display_name}%'})
                count = result.scalar()

                if count and count > 0:
                    existing.append(name)
                else:
                    logger.debug(f"No products found for {display_name}")

        except Exception as e:
            logger.error(f"Error checking bank existence: {e}")
        finally:
            db.close()

        return existing

    async def _fetch_and_compare_from_postgresql(
        self,
        target_banks: List[str],
        loan_type: str,
        user_conditions: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        PostgreSQL에서 은행별 대출 상품을 조회하고 비교 데이터 생성

        Args:
            target_banks: 조회할 은행명 리스트
            loan_type: 대출 유형
            user_conditions: 사용자 조건

        Returns:
            은행별 비교 데이터 리스트
        """
        bank_comparisons = []
        db = self.SessionLocal()

        try:
            # 대출 타입 별칭 가져오기
            loan_type_keywords = self.loan_type_aliases.get(loan_type, [loan_type])

            # 은행별로 조회
            for bank_name in target_banks:
                display_name = self.bank_display_names.get(bank_name, bank_name)

                # SQL 쿼리: 은행 + 대출 상품 검색 (별칭 포함)
                # ILIKE로 대소문자 구분 없이 검색
                keyword_conditions = " OR ".join([
                    f"(p.product_name ILIKE :keyword_{i} OR "
                    f"p.summary ILIKE :keyword_{i} OR "
                    f"pc.category_name ILIKE :keyword_{i})"
                    for i in range(len(loan_type_keywords))
                ])

                query = f"""
                    SELECT
                        b.bank_name,
                        p.product_id,
                        p.product_name,
                        p.summary,
                        pc.category_name as product_category,
                        p.last_updated,
                        array_agg(
                            json_build_object(
                                'chunk_id', cc.chunk_id,
                                'category', chc.category_name,
                                'content_text', cc.content_text
                            )
                        ) as content_chunks
                    FROM products p
                    JOIN banks b ON p.bank_id = b.id
                    JOIN product_categories pc ON p.product_category_id = pc.id
                    LEFT JOIN content_chunks cc ON p.id = cc.product_id
                    LEFT JOIN chunk_categories chc ON cc.chunk_category_id = chc.id
                    WHERE b.bank_name ILIKE :bank_name
                    AND ({keyword_conditions})
                    GROUP BY b.bank_name, p.product_id, p.product_name, p.summary,
                             pc.category_name, p.last_updated
                    LIMIT 3
                """

                # 파라미터 준비
                params = {'bank_name': f'%{display_name}%'}
                for i, keyword in enumerate(loan_type_keywords):
                    params[f'keyword_{i}'] = f'%{keyword}%'

                result = db.execute(text(query), params)
                products = result.fetchall()

                if not products:
                    logger.info(f"No {loan_type} products found for {display_name}")
                    continue

                # 각 상품에 대해 비교 데이터 생성
                for product in products:
                    comparison_data = self._create_comparison_from_postgres_row(
                        bank_name, product, user_conditions
                    )
                    if comparison_data:
                        bank_comparisons.append(comparison_data)

        except Exception as e:
            logger.error(f"Failed to fetch from PostgreSQL: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

        return bank_comparisons

    def _create_comparison_from_postgres_row(
        self,
        bank_name: str,
        product_row,
        user_conditions: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        PostgreSQL row에서 비교 데이터 생성

        Args:
            bank_name: 은행명
            product_row: PostgreSQL query result row
            user_conditions: 사용자 조건

        Returns:
            비교 데이터 딕셔너리
        """
        try:
            # Row를 dict로 변환
            bank_display_name = product_row[0]  # bank_name
            product_id = product_row[1]
            product_name = product_row[2]
            summary = product_row[3]
            product_category = product_row[4]
            last_updated = product_row[5]
            content_chunks_json = product_row[6]  # array of json objects

            # content_chunks를 리스트로 변환
            content_chunks = []
            if content_chunks_json:
                for chunk_json in content_chunks_json:
                    if chunk_json and chunk_json.get('content_text'):
                        content_chunks.append({
                            'chunk_id': chunk_json.get('chunk_id'),
                            'category': chunk_json.get('category'),
                            'content_text': chunk_json.get('content_text')
                        })

            # content_chunks에서 금리, 한도 정보 추출
            interest_rate_info = self._extract_interest_rate_from_chunks(content_chunks)
            loan_limit_info = self._extract_loan_limit_from_chunks(content_chunks)
            benefits_info = self._extract_benefits_from_chunks(content_chunks)

            # 사용자 조건에 따른 예상 금리 계산
            estimated_rate = self._estimate_rate_from_doc(
                interest_rate_info, user_conditions
            )

            # 사용자 조건에 따른 예상 한도 계산
            estimated_limit = self._estimate_limit_from_doc(
                loan_limit_info, user_conditions
            )

            return {
                "bank": bank_display_name,
                "product_name": product_name,
                "loan_type": product_category or "",
                "금리_범위": interest_rate_info.get("금리_범위"),
                "예상_금리": estimated_rate,
                "최대_한도": loan_limit_info.get("최대_한도"),
                "예상_한도": estimated_limit,
                "우대금리_조건": benefits_info.get("우대금리", []),
                "특징": benefits_info.get("특징", []),
                "LTV_최대": loan_limit_info.get("LTV_최대"),
                "source_url": "",  # PostgreSQL에는 URL 정보가 없을 수 있음
            }

        except Exception as e:
            logger.error(f"Failed to create comparison data: {e}")
            return None

    def _extract_interest_rate_from_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        content_chunks에서 금리 정보 추출

        은행별로 형식이 다름:
        - 하나은행: "기준금리: 3.661, 가산금리: 1.000" 형태
        - KB/신한/우리: "COFIX + 가산금리 - 우대금리" 설명 형태
        """
        import re

        rate_info = {"금리_범위": None, "raw_text": "", "rate_type": "unknown"}

        for chunk in chunks:
            category = chunk.get("category", "")
            content = chunk.get("content_text", "")

            if "대출금리" in category or "금리" in category:
                rate_info["raw_text"] += content + " "

                # 방법 1: 하나은행 형식 - "기준금리: X.XXX, 가산금리: Y.YYY"
                base_rate_match = re.search(r'기준금리\s*[:：]\s*(\d+\.?\d*)', content)
                add_rate_match = re.search(r'가산금리\s*[:：]\s*(\d+\.?\d*)', content)

                if base_rate_match and add_rate_match:
                    base_rate = float(base_rate_match.group(1))
                    add_rate = float(add_rate_match.group(1))
                    total_rate = base_rate + add_rate

                    rate_info["금리_범위"] = {
                        "min": round(total_rate - 0.5, 2),  # 우대금리 적용 가정
                        "max": round(total_rate, 2)
                    }
                    rate_info["rate_type"] = "fixed_structured"
                    continue

                # 방법 2: "최저 X% ~ 최고 Y%" 형태
                range_match = re.search(r'최저\s*(\d+\.?\d*)%?\s*~\s*최고\s*(\d+\.?\d*)%?', content)
                if range_match:
                    min_rate = float(range_match.group(1))
                    max_rate = float(range_match.group(2))

                    rate_info["금리_범위"] = {
                        "min": min_rate,
                        "max": max_rate
                    }
                    rate_info["rate_type"] = "range_specified"
                    continue

                # 방법 3: 일반적인 퍼센트 숫자 추출 (2% 이상만)
                rates = re.findall(r'(\d+\.?\d*)%', content)
                if rates and not rate_info["금리_범위"]:
                    rates_float = [float(r) for r in rates if float(r) >= 2.0]

                    if rates_float:
                        rate_info["금리_범위"] = {
                            "min": min(rates_float),
                            "max": max(rates_float)
                        }
                        rate_info["rate_type"] = "percent_extracted"

        # 기본값 설정 (COFIX 기준 전세대출 평균 금리)
        if not rate_info["금리_범위"]:
            rate_info["금리_범위"] = {"min": 3.5, "max": 5.5}
            rate_info["rate_type"] = "default"

        return rate_info

    def _extract_loan_limit_from_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """content_chunks에서 한도 정보 추출"""
        import re

        limit_info = {"최대_한도": None, "LTV_최대": None, "raw_text": ""}

        for chunk in chunks:
            category = chunk.get("category", "")
            content = chunk.get("content_text", "")

            if "대출한도" in category or "한도" in category:
                limit_info["raw_text"] += content + " "

                # LTV 추출 (예: 70%, 80% 등)
                ltv_match = re.search(r'LTV\s*(\d+)%', content, re.IGNORECASE)
                if ltv_match:
                    limit_info["LTV_최대"] = int(ltv_match.group(1)) / 100

                # 최대 한도 추출 (예: 10억, 5억 등)
                amount_match = re.search(r'(\d+(?:,\d+)?)\s*억', content)
                if amount_match:
                    amount_str = amount_match.group(1).replace(',', '')
                    limit_info["최대_한도"] = int(amount_str) * 100_000_000

        # 기본값 설정
        if not limit_info["최대_한도"]:
            limit_info["최대_한도"] = 10_000_000_000
        if not limit_info["LTV_최대"]:
            limit_info["LTV_최대"] = 0.7

        return limit_info

    def _extract_benefits_from_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """content_chunks에서 우대금리 및 특징 추출"""
        benefits = {"우대금리": [], "특징": []}

        for chunk in chunks:
            category = chunk.get("category", "")
            content = chunk.get("content_text", "")

            if "우대" in category or "혜택" in category:
                # 간단한 문장으로 분리
                sentences = content.split('.')
                for sentence in sentences[:3]:  # 최대 3개
                    sentence = sentence.strip()
                    if sentence and len(sentence) > 5:
                        benefits["우대금리"].append(sentence[:50])

            if "특징" in category or "장점" in category:
                sentences = content.split('.')
                for sentence in sentences[:2]:  # 최대 2개
                    sentence = sentence.strip()
                    if sentence and len(sentence) > 5:
                        benefits["특징"].append(sentence[:50])

        return benefits

    def _estimate_rate_from_doc(
        self,
        rate_info: Dict[str, Any],
        user_conditions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """MongoDB 문서에서 추출한 금리 정보로 예상 금리 계산"""
        rate_range = rate_info.get("금리_범위", {"min": 3.5, "max": 5.5})
        base_rate = (rate_range["min"] + rate_range["max"]) / 2

        if not user_conditions:
            return {
                "기본_금리": round(base_rate, 2),
                "최종_금리": round(base_rate, 2),
                "우대_할인": 0,
            }

        # 신용등급에 따른 금리 조정
        credit_score = user_conditions.get("credit_score", 3)
        if credit_score <= 2:
            rate_adjustment = -0.3
        elif credit_score == 3:
            rate_adjustment = 0
        elif credit_score == 4:
            rate_adjustment = 0.5
        else:
            rate_adjustment = 1.0

        # 우대금리 예상 (평균 -0.3% 가정)
        discount_estimate = 0.3

        final_rate = max(
            rate_range["min"],
            min(base_rate + rate_adjustment - discount_estimate, rate_range["max"])
        )

        return {
            "기본_금리": round(base_rate, 2),
            "신용등급_조정": round(rate_adjustment, 2),
            "우대_할인": round(discount_estimate, 2),
            "최종_금리": round(final_rate, 2),
        }

    def _estimate_limit_from_doc(
        self,
        limit_info: Dict[str, Any],
        user_conditions: Optional[Dict[str, Any]]
    ) -> Optional[int]:
        """MongoDB 문서에서 추출한 한도 정보로 예상 한도 계산"""
        if not user_conditions:
            return None

        annual_income = user_conditions.get("annual_income")
        property_price = user_conditions.get("property_price")

        if not annual_income or not property_price:
            return None

        # DSR 40% 기준 계산 (간단 추정)
        dsr_limit = int((annual_income / 12) * 0.4 * 12 * 20)  # 20년 가정

        # LTV 기준 계산
        ltv_max = limit_info.get("LTV_최대", 0.7)
        ltv_limit = int(property_price * ltv_max)

        # 상품 최대 한도
        product_max = limit_info.get("최대_한도", 10_000_000_000)

        # 최종 한도 (가장 작은 값)
        estimated = min(dsr_limit, ltv_limit, product_max)

        return estimated

    async def execute(
        self,
        banks: Optional[List[str]] = None,
        loan_type: str = "주택담보대출",
        user_conditions: Optional[Dict[str, Any]] = None,
        include_policy_loans: bool = True,
    ) -> Dict[str, Any]:
        """
        은행별 대출 조건 비교 실행

        Args:
            banks: 비교할 은행 리스트 (None이면 모든 은행)
            loan_type: 대출 유형 (주택담보대출, 전세자금대출 등)
            user_conditions: 사용자 조건 (연봉, 신용등급, DSR 등)
            include_policy_loans: 정책금융 포함 여부

        Returns:
            비교 결과
        """
        try:
            logger.info(f"Comparing loans: type={loan_type}, banks={banks}")

            # 비교할 은행 결정
            target_banks = self._normalize_bank_names(banks)

            # 1. PostgreSQL에서 은행별 대출 상품 조회
            bank_comparisons = await self._fetch_and_compare_from_postgresql(
                target_banks, loan_type, user_conditions
            )

            # 2. 정책금융 포함
            policy_comparisons = []
            if include_policy_loans:
                for policy_name, policy_data in self.policy_loans.items():
                    estimated_rate = self._estimate_rate(policy_data, user_conditions)
                    estimated_limit = self._estimate_limit(policy_data, user_conditions)

                    policy_comparisons.append({
                        "상품명": policy_name,
                        "금리_범위": policy_data["금리_범위"],
                        "예상_금리": estimated_rate,
                        "최대_한도": policy_data["최대_한도"],
                        "예상_한도": estimated_limit,
                        "대상": policy_data.get("대상"),
                        "특징": policy_data.get("특징", []),
                        "LTV_최대": policy_data.get("LTV_최대"),
                    })

            # 3. 비교 분석
            comparison_analysis = self._analyze_comparison(
                bank_comparisons, policy_comparisons, user_conditions
            )

            # 4. 추천 상품 선정
            recommendations = self._generate_recommendations(
                bank_comparisons, policy_comparisons, user_conditions
            )

            # 5. 종합 인사이트
            insights = self._generate_insights(
                bank_comparisons, policy_comparisons, user_conditions
            )

            return {
                "status": "success",
                "loan_type": loan_type,
                "requested_banks": banks,
                "bank_comparisons": sorted(
                    bank_comparisons,
                    key=lambda x: x.get("예상_금리", {}).get("최종_금리", 999)
                ),
                "policy_loans": policy_comparisons,
                "comparison_analysis": comparison_analysis,
                "recommendations": recommendations,
                "insights": insights,
                "user_conditions": user_conditions,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Loan comparison failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "loan_type": loan_type,
                "timestamp": datetime.now().isoformat(),
            }

    def _estimate_rate(
        self, product: Dict[str, Any], user_conditions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """사용자 조건에 따른 예상 금리 계산"""
        rate_range = product["금리_범위"]
        base_rate = (rate_range["min"] + rate_range["max"]) / 2

        if not user_conditions:
            return {
                "기본_금리": round(base_rate, 2),
                "최종_금리": round(base_rate, 2),
                "우대_할인": 0,
            }

        # 신용등급에 따른 금리 조정
        credit_score = user_conditions.get("credit_score", 3)
        if credit_score <= 2:
            rate_adjustment = -0.3
        elif credit_score == 3:
            rate_adjustment = 0
        elif credit_score == 4:
            rate_adjustment = 0.5
        else:
            rate_adjustment = 1.0

        # 우대금리 예상 (평균 -0.3% 가정)
        discount_estimate = 0.3

        final_rate = max(
            rate_range["min"],
            min(base_rate + rate_adjustment - discount_estimate, rate_range["max"])
        )

        return {
            "기본_금리": round(base_rate, 2),
            "신용등급_조정": round(rate_adjustment, 2),
            "우대_할인": round(discount_estimate, 2),
            "최종_금리": round(final_rate, 2),
        }

    def _estimate_limit(
        self, product: Dict[str, Any], user_conditions: Optional[Dict[str, Any]]
    ) -> Optional[int]:
        """사용자 조건에 따른 예상 한도 계산"""
        if not user_conditions:
            return None

        annual_income = user_conditions.get("annual_income")
        property_price = user_conditions.get("property_price")

        if not annual_income or not property_price:
            return None

        # DSR 40% 기준 계산 (간단 추정)
        dsr_limit = int((annual_income / 12) * 0.4 * 12 * 20)  # 20년 가정

        # LTV 기준 계산
        ltv_max = product.get("LTV_최대", 0.7)
        ltv_limit = int(property_price * ltv_max)

        # 상품 최대 한도
        product_max = product.get("최대_한도", 10_000_000_000)

        # 최종 한도 (가장 작은 값)
        estimated = min(dsr_limit, ltv_limit, product_max)

        return estimated

    def _analyze_comparison(
        self,
        bank_comparisons: List[Dict],
        policy_comparisons: List[Dict],
        user_conditions: Optional[Dict],
    ) -> Dict[str, Any]:
        """비교 분석 수행"""
        if not bank_comparisons:
            return {}

        # 최저 금리
        lowest_rate_bank = min(
            bank_comparisons,
            key=lambda x: x.get("예상_금리", {}).get("최종_금리", 999),
        )

        # 최고 한도
        highest_limit_bank = max(
            bank_comparisons,
            key=lambda x: x.get("예상_한도") or 0,
        )

        # 금리 범위
        rates = [
            b.get("예상_금리", {}).get("최종_금리", 0)
            for b in bank_comparisons
        ]
        rate_spread = max(rates) - min(rates) if rates else 0

        return {
            "최저_금리": {
                "은행": lowest_rate_bank["bank"],
                "금리": lowest_rate_bank.get("예상_금리", {}).get("최종_금리"),
            },
            "최고_한도": {
                "은행": highest_limit_bank["bank"],
                "한도": highest_limit_bank.get("예상_한도"),
            },
            "금리_차이": round(rate_spread, 2),
            "비교_은행_수": len(bank_comparisons),
            "정책금융_수": len(policy_comparisons),
        }

    def _generate_recommendations(
        self,
        bank_comparisons: List[Dict],
        policy_comparisons: List[Dict],
        user_conditions: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """추천 상품 생성"""
        recommendations = []

        # 1순위: 정책금융 (조건 충족시)
        if policy_comparisons and user_conditions:
            # 디딤돌대출 추천 (저소득층)
            annual_income = user_conditions.get("annual_income", 0)
            if annual_income < 85_000_000:  # 8500만원 이하
                for policy in policy_comparisons:
                    if "디딤돌" in policy["상품명"]:
                        recommendations.append({
                            "순위": 1,
                            "상품": policy["상품명"],
                            "이유": "초저금리 정책금융으로 금리 부담 최소화",
                            "예상_금리": policy.get("예상_금리", {}).get("최종_금리"),
                            "특징": policy.get("특징", []),
                        })
                        break

        # 2순위: 최저 금리 은행
        if bank_comparisons:
            lowest = min(
                bank_comparisons,
                key=lambda x: x.get("예상_금리", {}).get("최종_금리", 999),
            )
            if not any(r["순위"] == 1 for r in recommendations):
                rank = 1
            else:
                rank = 2

            recommendations.append({
                "순위": rank,
                "상품": f"{lowest['bank']} {lowest['loan_type']}",
                "이유": "비교 은행 중 최저 금리",
                "예상_금리": lowest.get("예상_금리", {}).get("최종_금리"),
                "우대_조건": lowest.get("우대금리_조건", []),
            })

        # 3순위: 최대 한도 은행 (한도가 중요한 경우)
        if bank_comparisons:
            highest = max(
                bank_comparisons,
                key=lambda x: x.get("예상_한도") or 0,
            )
            if highest["bank"] != (recommendations[-1]["상품"].split()[0] if recommendations else ""):
                recommendations.append({
                    "순위": len(recommendations) + 1,
                    "상품": f"{highest['bank']} {highest['loan_type']}",
                    "이유": "최대 한도 제공",
                    "예상_한도": highest.get("예상_한도"),
                    "특징": highest.get("특징", []),
                })

        return recommendations[:3]  # 상위 3개만

    def _generate_insights(
        self,
        bank_comparisons: List[Dict],
        policy_comparisons: List[Dict],
        user_conditions: Optional[Dict],
    ) -> List[str]:
        """종합 인사이트 생성"""
        insights = []

        # 금리 차이 분석
        if bank_comparisons:
            rates = [
                b.get("예상_금리", {}).get("최종_금리", 0)
                for b in bank_comparisons
            ]
            rate_spread = max(rates) - min(rates)
            if rate_spread > 0.5:
                insights.append(
                    f"은행별 금리 차이가 최대 {rate_spread:.2f}%p입니다. "
                    "신중한 비교가 필요합니다."
                )

        # 우대금리 활용 팁
        insights.append(
            "급여이체, 카드사용 등 우대조건 활용시 최대 0.5~1.0%p 금리 할인이 가능합니다."
        )

        # 정책금융 안내
        if policy_comparisons:
            insights.append(
                "주택금융공사 정책금융(디딤돌, 보금자리론)은 시중은행 대비 "
                "0.5~1.5%p 낮은 금리를 제공합니다."
            )

        # DSR 규제 안내
        if user_conditions and user_conditions.get("annual_income"):
            insights.append(
                "DSR(총부채원리금상환비율) 40% 규제로 인해 소득 대비 상환액이 제한됩니다. "
                "기존 대출이 있다면 한도가 감소할 수 있습니다."
            )

        # 여러 은행 상담 권장
        insights.append(
            "실제 대출 조건은 은행별 심사 기준에 따라 달라질 수 있으므로, "
            "2~3개 은행에 직접 상담받는 것을 권장합니다."
        )

        return insights[:5]  # 최대 5개


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_loan_comparison():
        tool = LoanComparisonTool()

        # 테스트 케이스 1: 특정 은행 비교
        print("=== 테스트 1: KB, 신한, 우리 주택담보대출 비교 ===")
        result1 = await tool.execute(
            banks=["KB", "신한", "우리"],
            loan_type="주택담보대출",
            user_conditions={
                "annual_income": 100_000_000,  # 연소득 1억
                "property_price": 800_000_000,  # 8억
                "credit_score": 2,
            },
        )

        print(f"Status: {result1['status']}")
        print(f"\n비교 결과:")
        for comp in result1["bank_comparisons"]:
            print(f"  - {comp['bank']}: 예상금리 {comp['예상_금리']['최종_금리']}%")

        print(f"\n추천 상품:")
        for rec in result1["recommendations"]:
            print(f"  {rec['순위']}. {rec['상품']} - {rec['이유']}")

        # 테스트 케이스 2: 전체 은행 + 정책금융
        print("\n\n=== 테스트 2: 전체 은행 전세자금대출 비교 ===")
        result2 = await tool.execute(
            loan_type="전세자금대출",
            user_conditions={
                "annual_income": 50_000_000,
                "property_price": 400_000_000,
                "credit_score": 3,
            },
            include_policy_loans=True,
        )

        print(f"비교 은행 수: {result2['comparison_analysis']['비교_은행_수']}")
        print(f"금리 차이: {result2['comparison_analysis']['금리_차이']}%p")

    asyncio.run(test_loan_comparison())
