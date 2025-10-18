"""
정부 지원 정책 매칭 Tool
사용자 조건에 맞는 정부 지원 정책 및 혜택 매칭
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from enum import Enum

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """정책 유형"""
    LOAN_SUPPORT = "대출지원"
    TAX_BENEFIT = "세제혜택"
    SUBSIDY = "보조금"
    PUBLIC_HOUSING = "공공주택"
    SPECIAL_SUPPLY = "특별공급"


class PolicyMatcherTool:
    """
    정부 정책 매칭 도구
    사용자 프로필 기반 지원 가능 정책 추천
    """

    def __init__(self, policy_search_tool=None):
        """
        초기화

        Args:
            policy_search_tool: 정책 검색 도구 (선택적)
        """
        self.policy_search_tool = policy_search_tool
        self.name = "policy_matcher"

        # 2024년 주요 정부 정책 데이터베이스
        self.policies = self._initialize_policy_database()

        logger.info(f"PolicyMatcherTool initialized with {len(self.policies)} policies")

    def _initialize_policy_database(self) -> List[Dict]:
        """정책 데이터베이스 초기화"""
        return [
            # === 대출 지원 정책 ===
            {
                "id": "디딤돌대출",
                "name": "디딤돌대출",
                "type": PolicyType.LOAN_SUPPORT,
                "provider": "주택도시기금",
                "target": ["무주택자", "신혼부부", "청년"],
                "conditions": {
                    "age": {"min": 19},
                    "income": {"max": 60000000},  # 부부합산 6천만원
                    "assets": {"max": 391000000},  # 3.91억
                    "housing": "무주택",
                    "marriage_years": {"신혼부부": 7}
                },
                "benefits": {
                    "interest_rate": {"min": 2.15, "max": 3.3},
                    "loan_limit": 250000000,  # 최대 2.5억
                    "loan_term": 30
                },
                "special_benefits": {
                    "신혼부부": "금리 0.2%p 우대",
                    "다자녀": "금리 0.5%p 우대",
                    "청년": "금리 0.2%p 우대"
                },
                "application_method": "은행 방문 또는 온라인",
                "deadline": "상시",
                "url": "https://nhuf.molit.go.kr"
            },
            {
                "id": "보금자리론",
                "name": "보금자리론",
                "type": PolicyType.LOAN_SUPPORT,
                "provider": "한국주택금융공사",
                "target": ["무주택자", "1주택자"],
                "conditions": {
                    "age": {"min": 19},
                    "income": {"max": 70000000},
                    "housing_price": {"max": 900000000},  # 9억 이하
                    "ltv": {"max": 0.7}
                },
                "benefits": {
                    "interest_rate": {"min": 3.7, "max": 4.5},
                    "loan_limit": 500000000,
                    "loan_term": 40
                },
                "special_benefits": {
                    "우대형": "소득 6천만 이하 금리우대"
                },
                "application_method": "시중은행 방문",
                "deadline": "상시",
                "url": "https://www.hf.go.kr"
            },
            {
                "id": "전세자금대출",
                "name": "버팀목 전세자금대출",
                "type": PolicyType.LOAN_SUPPORT,
                "provider": "주택도시기금",
                "target": ["무주택자", "청년", "신혼부부"],
                "conditions": {
                    "age": {"min": 19},
                    "income": {"max": 50000000},  # 5천만원
                    "assets": {"max": 292000000},  # 2.92억
                    "deposit": {"max": 300000000}  # 수도권 3억
                },
                "benefits": {
                    "interest_rate": {"min": 1.8, "max": 2.7},
                    "loan_limit": 120000000,  # 최대 1.2억
                    "loan_ratio": 0.8  # 보증금의 80%
                },
                "special_benefits": {
                    "청년": "금리 0.5%p 우대",
                    "신혼부부": "한도 2.2억까지 확대"
                },
                "application_method": "은행 방문",
                "deadline": "상시",
                "url": "https://nhuf.molit.go.kr"
            },

            # === 청년 특화 정책 ===
            {
                "id": "청년월세지원",
                "name": "청년월세 한시 특별지원",
                "type": PolicyType.SUBSIDY,
                "provider": "국토교통부",
                "target": ["청년"],
                "conditions": {
                    "age": {"min": 19, "max": 34},
                    "income": {"max": 27840000},  # 중위소득 60%
                    "assets": {"max": 107000000},
                    "housing": "무주택",
                    "education_employment": "대학생 또는 취업준비생"
                },
                "benefits": {
                    "monthly_support": 200000,  # 월 최대 20만원
                    "support_period": 12  # 12개월
                },
                "application_method": "복지로 온라인 신청",
                "deadline": "2024.12.31",
                "url": "https://www.bokjiro.go.kr"
            },
            {
                "id": "청년전세임대",
                "name": "청년 전세임대주택",
                "type": PolicyType.PUBLIC_HOUSING,
                "provider": "LH/SH",
                "target": ["청년"],
                "conditions": {
                    "age": {"min": 19, "max": 39},
                    "income": {"max": 46320000},  # 중위소득 100%
                    "housing": "무주택"
                },
                "benefits": {
                    "deposit_support": {"max": 120000000},
                    "rent": "시세 50% 수준",
                    "residence_period": 6  # 최대 6년
                },
                "application_method": "LH/SH 청약센터",
                "deadline": "수시 모집",
                "url": "https://www.lh.or.kr"
            },

            # === 신혼부부 특화 정책 ===
            {
                "id": "신혼부부전용대출",
                "name": "신혼부부 전용 디딤돌대출",
                "type": PolicyType.LOAN_SUPPORT,
                "provider": "주택도시기금",
                "target": ["신혼부부"],
                "conditions": {
                    "marriage_years": {"max": 7},
                    "income": {"max": 70000000},
                    "housing": "무주택"
                },
                "benefits": {
                    "interest_rate": {"min": 1.85, "max": 2.7},
                    "loan_limit": 400000000,
                    "loan_term": 30
                },
                "special_benefits": {
                    "출산": "자녀 1명당 금리 0.2%p 추가 인하"
                },
                "application_method": "은행 방문",
                "deadline": "상시",
                "url": "https://nhuf.molit.go.kr"
            },
            {
                "id": "신혼희망타운",
                "name": "신혼희망타운",
                "type": PolicyType.SPECIAL_SUPPLY,
                "provider": "LH",
                "target": ["신혼부부", "예비신혼부부"],
                "conditions": {
                    "marriage_years": {"max": 7},
                    "income": {"max": 130000000},  # 도시근로자 월평균소득 130%
                    "assets": {"max": 330000000},
                    "housing": "무주택"
                },
                "benefits": {
                    "price": "시세 70~80% 수준",
                    "area": "전용 55~85㎡",
                    "ownership": "분양전환 가능"
                },
                "application_method": "LH 청약센터",
                "deadline": "공고시 확인",
                "url": "https://www.lh.or.kr"
            },

            # === 세제 혜택 ===
            {
                "id": "생애최초취득세감면",
                "name": "생애최초 주택구입 취득세 감면",
                "type": PolicyType.TAX_BENEFIT,
                "provider": "지방자치단체",
                "target": ["생애최초구매자"],
                "conditions": {
                    "housing": "생애최초",
                    "housing_price": {"max": 900000000},
                    "area": {"max": 60}  # 전용 60㎡ 이하
                },
                "benefits": {
                    "tax_reduction": 0.5,  # 50% 감면
                    "max_reduction": 2000000  # 최대 200만원
                },
                "application_method": "주택 취득시 자동 적용",
                "deadline": "2024.12.31",
                "url": "지자체별 상이"
            },
            {
                "id": "청약통장소득공제",
                "name": "청약저축 소득공제",
                "type": PolicyType.TAX_BENEFIT,
                "provider": "국세청",
                "target": ["무주택자"],
                "conditions": {
                    "income": {"max": 70000000},
                    "housing": "무주택"
                },
                "benefits": {
                    "deduction_rate": 0.4,  # 40% 소득공제
                    "max_deduction": 2400000  # 연 240만원 한도
                },
                "application_method": "연말정산시 자동 적용",
                "deadline": "상시",
                "url": "https://www.nts.go.kr"
            },

            # === 특별공급 ===
            {
                "id": "다자녀특별공급",
                "name": "다자녀가구 특별공급",
                "type": PolicyType.SPECIAL_SUPPLY,
                "provider": "각 건설사",
                "target": ["다자녀가구"],
                "conditions": {
                    "children": {"min": 2},  # 미성년 자녀 2명 이상
                    "housing": "무주택",
                    "residence": "해당지역 거주"
                },
                "benefits": {
                    "supply_ratio": 0.1,  # 전체 물량의 10%
                    "priority": "자녀수 많을수록 우선"
                },
                "application_method": "청약홈",
                "deadline": "분양공고시",
                "url": "https://www.applyhome.co.kr"
            },
            {
                "id": "노부모부양특별공급",
                "name": "노부모부양 특별공급",
                "type": PolicyType.SPECIAL_SUPPLY,
                "provider": "각 건설사",
                "target": ["노부모부양자"],
                "conditions": {
                    "parent_age": {"min": 65},
                    "support_years": {"min": 3},
                    "housing": "무주택"
                },
                "benefits": {
                    "supply_ratio": 0.03,  # 전체 물량의 3%
                    "priority": "부양기간 우선"
                },
                "application_method": "청약홈",
                "deadline": "분양공고시",
                "url": "https://www.applyhome.co.kr"
            }
        ]

    async def execute(
        self,
        user_profile: Dict[str, Any],
        policy_types: Optional[List[str]] = None,
        search_additional: bool = False
    ) -> Dict[str, Any]:
        """
        정책 매칭 실행

        Args:
            user_profile: 사용자 프로필 정보
            policy_types: 검색할 정책 유형 (없으면 전체)
            search_additional: 추가 정책 온라인 검색 여부

        Returns:
            매칭된 정책 정보
        """
        try:
            logger.info(f"Matching policies for user profile")

            # 1. 사용자 프로필 분석
            analyzed_profile = self._analyze_user_profile(user_profile)

            # 2. 정책 매칭
            matched_policies = self._match_policies(analyzed_profile, policy_types)

            # 3. 우선순위 정렬
            prioritized = self._prioritize_policies(matched_policies, analyzed_profile)

            # 4. 추가 정책 검색 (옵션)
            additional_policies = []
            if search_additional and self.policy_search_tool:
                additional_policies = await self._search_additional_policies(
                    analyzed_profile
                )

            # 5. 혜택 계산
            benefit_summary = self._calculate_total_benefits(
                prioritized, analyzed_profile
            )

            # 6. 신청 가이드 생성
            application_guide = self._generate_application_guide(
                prioritized[:3]  # 상위 3개
            )

            # 7. 추천 이유 생성
            recommendations = self._generate_recommendations(
                prioritized, analyzed_profile
            )

            return {
                "status": "success",
                "user_profile": analyzed_profile,
                "matched_policies": prioritized,
                "additional_policies": additional_policies,
                "total_matched": len(prioritized),
                "benefit_summary": benefit_summary,
                "application_guide": application_guide,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Policy matching failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _analyze_user_profile(self, profile: Dict) -> Dict:
        """사용자 프로필 분석"""
        analyzed = profile.copy()

        # 나이 그룹 판별
        age = profile.get("age", 0)
        if 19 <= age <= 34:
            analyzed["age_group"] = "청년"
        elif 35 <= age <= 39:
            analyzed["age_group"] = "청년(확대)"
        elif age >= 65:
            analyzed["age_group"] = "고령자"
        else:
            analyzed["age_group"] = "일반"

        # 가구 특성 판별
        household_types = []

        if profile.get("marriage_years", 999) <= 7:
            household_types.append("신혼부부")

        if profile.get("children", 0) >= 2:
            household_types.append("다자녀가구")

        if profile.get("children", 0) == 1:
            household_types.append("1자녀가구")

        if profile.get("is_single_parent"):
            household_types.append("한부모가족")

        if profile.get("has_disability"):
            household_types.append("장애인가구")

        if not profile.get("has_house", True):
            household_types.append("무주택자")

        if profile.get("first_time_buyer"):
            household_types.append("생애최초구매자")

        analyzed["household_types"] = household_types

        # 소득 수준 판별
        income = profile.get("annual_income", 0)
        if income <= 27840000:
            analyzed["income_level"] = "중위소득 60% 이하"
        elif income <= 46320000:
            analyzed["income_level"] = "중위소득 100% 이하"
        elif income <= 69480000:
            analyzed["income_level"] = "중위소득 150% 이하"
        else:
            analyzed["income_level"] = "중위소득 150% 초과"

        return analyzed

    def _match_policies(
        self,
        profile: Dict,
        policy_types: Optional[List[str]]
    ) -> List[Dict]:
        """정책 매칭"""
        matched = []

        for policy in self.policies:
            # 정책 유형 필터
            if policy_types and policy["type"].value not in policy_types:
                continue

            # 대상 확인
            if not self._check_target_match(policy["target"], profile):
                continue

            # 조건 확인
            if not self._check_conditions(policy["conditions"], profile):
                continue

            # 매칭 점수 계산
            match_score = self._calculate_match_score(policy, profile)

            matched_policy = policy.copy()
            matched_policy["match_score"] = match_score
            matched_policy["eligible"] = True
            matched.append(matched_policy)

        return matched

    def _check_target_match(self, targets: List[str], profile: Dict) -> bool:
        """대상 매칭 확인"""
        household_types = profile.get("household_types", [])

        for target in targets:
            if target == "무주택자" and "무주택자" in household_types:
                return True
            elif target == "청년" and profile.get("age_group") in ["청년", "청년(확대)"]:
                return True
            elif target == "신혼부부" and "신혼부부" in household_types:
                return True
            elif target == "다자녀가구" and "다자녀가구" in household_types:
                return True
            elif target == "생애최초구매자" and "생애최초구매자" in household_types:
                return True
            elif target == "1주택자" and profile.get("house_count", 0) == 1:
                return True
            elif target == "노부모부양자" and profile.get("support_parent"):
                return True

        return False

    def _check_conditions(self, conditions: Dict, profile: Dict) -> bool:
        """조건 충족 확인"""
        # 나이 조건
        if "age" in conditions:
            age = profile.get("age", 0)
            if "min" in conditions["age"] and age < conditions["age"]["min"]:
                return False
            if "max" in conditions["age"] and age > conditions["age"]["max"]:
                return False

        # 소득 조건
        if "income" in conditions:
            income = profile.get("annual_income", 0)
            if "max" in conditions["income"] and income > conditions["income"]["max"]:
                return False
            if "min" in conditions["income"] and income < conditions["income"]["min"]:
                return False

        # 자산 조건
        if "assets" in conditions:
            assets = profile.get("total_assets", 0)
            if "max" in conditions["assets"] and assets > conditions["assets"]["max"]:
                return False

        # 주택 조건
        if "housing" in conditions:
            if conditions["housing"] == "무주택" and profile.get("has_house", True):
                return False

        # 결혼 기간 조건
        if "marriage_years" in conditions:
            years = profile.get("marriage_years", 999)
            if isinstance(conditions["marriage_years"], dict):
                if "max" in conditions["marriage_years"] and years > conditions["marriage_years"]["max"]:
                    return False
            else:
                # 신혼부부 특별 케이스
                if years > conditions["marriage_years"]:
                    return False

        # 자녀 조건
        if "children" in conditions:
            children = profile.get("children", 0)
            if "min" in conditions["children"] and children < conditions["children"]["min"]:
                return False

        return True

    def _calculate_match_score(self, policy: Dict, profile: Dict) -> float:
        """매칭 점수 계산"""
        score = 50.0  # 기본 점수

        # 정책 유형별 가중치
        type_weights = {
            PolicyType.LOAN_SUPPORT: 20,
            PolicyType.SUBSIDY: 15,
            PolicyType.TAX_BENEFIT: 10,
            PolicyType.PUBLIC_HOUSING: 15,
            PolicyType.SPECIAL_SUPPLY: 10
        }
        score += type_weights.get(policy["type"], 0)

        # 특별 혜택 가중치
        if "special_benefits" in policy:
            for benefit_target in policy["special_benefits"]:
                if benefit_target in profile.get("household_types", []):
                    score += 10

        # 소득 적합도
        if "income" in policy["conditions"] and "max" in policy["conditions"]["income"]:
            income = profile.get("annual_income", 0)
            max_income = policy["conditions"]["income"]["max"]
            if income < max_income * 0.5:
                score += 10  # 소득이 제한의 50% 이하면 가점
            elif income < max_income * 0.8:
                score += 5

        # 긴급도 (마감일 임박)
        if policy.get("deadline") and policy["deadline"] != "상시":
            try:
                deadline = datetime.strptime(policy["deadline"], "%Y.%m.%d")
                days_left = (deadline - datetime.now()).days
                if days_left < 30:
                    score += 15  # 마감 임박 가점
                elif days_left < 90:
                    score += 5
            except:
                pass

        return min(100, score)

    def _prioritize_policies(
        self,
        policies: List[Dict],
        profile: Dict
    ) -> List[Dict]:
        """정책 우선순위 정렬"""
        # 점수 기준 정렬
        sorted_policies = sorted(
            policies,
            key=lambda x: x["match_score"],
            reverse=True
        )

        # 우선순위 부여
        for i, policy in enumerate(sorted_policies):
            policy["priority"] = i + 1
            policy["priority_reason"] = self._get_priority_reason(policy, profile)

        return sorted_policies

    def _calculate_total_benefits(
        self,
        policies: List[Dict],
        profile: Dict
    ) -> Dict[str, Any]:
        """총 혜택 계산"""
        total_loan_limit = 0
        min_interest_rate = 999
        total_subsidy = 0
        total_tax_benefit = 0

        for policy in policies:
            benefits = policy.get("benefits", {})

            # 대출 한도 합산
            if "loan_limit" in benefits:
                total_loan_limit = max(total_loan_limit, benefits["loan_limit"])

            # 최저 금리
            if "interest_rate" in benefits:
                min_rate = benefits["interest_rate"].get("min", 999)
                min_interest_rate = min(min_interest_rate, min_rate)

            # 보조금 합산
            if "monthly_support" in benefits:
                period = benefits.get("support_period", 12)
                total_subsidy += benefits["monthly_support"] * period

            # 세제 혜택
            if "max_reduction" in benefits:
                total_tax_benefit += benefits["max_reduction"]
            elif "max_deduction" in benefits:
                # 소득공제 -> 세액 절감 추정 (15% 세율 가정)
                total_tax_benefit += benefits["max_deduction"] * 0.15

        return {
            "max_loan_amount": total_loan_limit,
            "min_interest_rate": min_interest_rate if min_interest_rate < 999 else None,
            "total_subsidy": total_subsidy,
            "estimated_tax_benefit": round(total_tax_benefit),
            "total_policies": len(policies)
        }

    def _generate_application_guide(self, top_policies: List[Dict]) -> List[Dict]:
        """신청 가이드 생성"""
        guide = []

        for policy in top_policies:
            guide_item = {
                "policy_name": policy["name"],
                "priority": policy["priority"],
                "application_steps": self._get_application_steps(policy),
                "required_documents": self._get_required_documents(policy),
                "application_method": policy.get("application_method"),
                "deadline": policy.get("deadline"),
                "url": policy.get("url"),
                "tips": self._get_application_tips(policy)
            }
            guide.append(guide_item)

        return guide

    def _get_application_steps(self, policy: Dict) -> List[str]:
        """신청 절차 생성"""
        if policy["type"] == PolicyType.LOAN_SUPPORT:
            return [
                "자격 요건 확인",
                "필요 서류 준비",
                "취급 은행 방문 또는 온라인 신청",
                "심사 진행",
                "승인 및 대출 실행"
            ]
        elif policy["type"] == PolicyType.SUBSIDY:
            return [
                "복지로 사이트 접속",
                "자격 확인 및 신청서 작성",
                "필요 서류 업로드",
                "심사 대기",
                "승인 및 지급"
            ]
        elif policy["type"] == PolicyType.SPECIAL_SUPPLY:
            return [
                "청약홈 가입 및 청약통장 확인",
                "분양 공고 확인",
                "특별공급 신청",
                "서류 제출",
                "당첨자 발표"
            ]
        else:
            return ["해당 기관 문의"]

    def _get_required_documents(self, policy: Dict) -> List[str]:
        """필요 서류 목록"""
        basic_docs = [
            "신분증",
            "주민등록등본",
            "소득증명서류"
        ]

        if "무주택" in str(policy.get("conditions", {})):
            basic_docs.append("무주택 확인서")

        if "신혼부부" in policy.get("target", []):
            basic_docs.append("혼인관계증명서")

        if "children" in policy.get("conditions", {}):
            basic_docs.append("가족관계증명서")

        return basic_docs

    def _get_application_tips(self, policy: Dict) -> List[str]:
        """신청 팁"""
        tips = []

        if policy.get("deadline") and policy["deadline"] != "상시":
            tips.append(f"마감일({policy['deadline']}) 전에 신청하세요")

        if "special_benefits" in policy:
            tips.append("추가 혜택 조건을 확인하세요")

        if policy["type"] == PolicyType.LOAN_SUPPORT:
            tips.append("여러 은행의 조건을 비교해보세요")

        return tips

    def _generate_recommendations(
        self,
        policies: List[Dict],
        profile: Dict
    ) -> List[Dict]:
        """추천 이유 생성"""
        recommendations = []

        for policy in policies[:5]:  # 상위 5개
            reason = {
                "policy_name": policy["name"],
                "match_score": policy["match_score"],
                "key_benefits": [],
                "why_recommended": policy.get("priority_reason", "")
            }

            # 주요 혜택 추출
            benefits = policy.get("benefits", {})
            if "interest_rate" in benefits:
                reason["key_benefits"].append(
                    f"금리 {benefits['interest_rate']['min']}%~"
                )
            if "loan_limit" in benefits:
                reason["key_benefits"].append(
                    f"한도 {benefits['loan_limit']/100000000:.1f}억"
                )
            if "monthly_support" in benefits:
                reason["key_benefits"].append(
                    f"월 {benefits['monthly_support']/10000}만원 지원"
                )

            recommendations.append(reason)

        return recommendations

    def _get_priority_reason(self, policy: Dict, profile: Dict) -> str:
        """우선순위 이유"""
        reasons = []

        if policy["match_score"] >= 80:
            reasons.append("매우 높은 적합도")

        if policy["type"] == PolicyType.LOAN_SUPPORT:
            reasons.append("대출 지원으로 자금 조달 용이")
        elif policy["type"] == PolicyType.SUBSIDY:
            reasons.append("직접적인 금전 지원")

        if "청년" in profile.get("household_types", []) and "청년" in policy.get("target", []):
            reasons.append("청년 맞춤 정책")

        if "신혼부부" in profile.get("household_types", []) and "신혼부부" in policy.get("target", []):
            reasons.append("신혼부부 특화 혜택")

        return ", ".join(reasons) if reasons else "조건 충족"

    async def _search_additional_policies(self, profile: Dict) -> List[Dict]:
        """추가 정책 온라인 검색"""
        try:
            if not self.policy_search_tool:
                return []

            # 검색 키워드 생성
            keywords = []
            if "청년" in profile.get("household_types", []):
                keywords.append("청년 주거 지원")
            if "신혼부부" in profile.get("household_types", []):
                keywords.append("신혼부부 주택")
            if "무주택자" in profile.get("household_types", []):
                keywords.append("무주택자 지원")

            results = await self.policy_search_tool.search(
                query=" ".join(keywords),
                limit=10
            )

            return results.get("policies", [])

        except Exception as e:
            logger.error(f"Additional policy search failed: {e}")
            return []


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_policy_matcher():
        matcher = PolicyMatcherTool()

        # 테스트 프로필 - 청년 신혼부부
        user_profile = {
            "age": 32,
            "annual_income": 55000000,  # 5500만원
            "total_assets": 200000000,   # 2억
            "has_house": False,
            "first_time_buyer": True,
            "marriage_years": 2,
            "children": 1,
            "region": "서울"
        }

        result = await matcher.execute(user_profile)

        print("=== Policy Matching Result ===")
        print(f"Status: {result['status']}")
        print(f"Total matched policies: {result['total_matched']}")

        print("\n사용자 프로필 분석:")
        profile = result['user_profile']
        print(f"  연령 그룹: {profile['age_group']}")
        print(f"  가구 유형: {', '.join(profile['household_types'])}")
        print(f"  소득 수준: {profile['income_level']}")

        print("\n매칭된 정책 (상위 3개):")
        for policy in result['matched_policies'][:3]:
            print(f"\n  {policy['priority']}. {policy['name']}")
            print(f"     유형: {policy['type'].value}")
            print(f"     매칭 점수: {policy['match_score']:.1f}")
            print(f"     추천 이유: {policy['priority_reason']}")

        print("\n총 혜택 요약:")
        benefits = result['benefit_summary']
        print(f"  최대 대출 한도: {benefits['max_loan_amount']/100000000:.1f}억")
        print(f"  최저 금리: {benefits['min_interest_rate']}%")
        print(f"  예상 세제 혜택: {benefits['estimated_tax_benefit']:,}원")

    asyncio.run(test_policy_matcher())