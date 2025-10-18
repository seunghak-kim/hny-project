"""
계약서 조항 분석 및 위험요소 탐지 Tool
법률 조항과 계약서 내용을 비교 분석하여 위험 요소를 탐지
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContractAnalysisTool:
    """
    계약서 조항 분석 도구
    계약서 텍스트를 분석하여 위험요소, 불법조항, 개선사항 추출
    """

    def __init__(self, legal_search_tool=None, llm_service=None):
        """
        초기화

        Args:
            legal_search_tool: 법률 검색 도구 (선택적)
            llm_service: LLM 서비스 (선택적)
        """
        self.legal_search_tool = legal_search_tool
        self.llm_service = llm_service
        self.name = "contract_analysis"

        # 주요 체크 항목
        self.key_clauses = [
            "보증금", "월세", "계약기간", "특약사항",
            "수리의무", "원상복구", "중도해지", "갱신",
            "관리비", "보증보험", "확정일자", "대항력"
        ]

        # 위험 키워드
        self.risk_keywords = [
            "위약금", "손해배상", "즉시", "포기", "일방적",
            "무조건", "절대", "어떠한 경우에도", "책임지지 않",
            "청구할 수 없", "이의를 제기할 수 없"
        ]

        logger.info("ContractAnalysisTool initialized")

    async def execute(
        self,
        contract_text: str,
        contract_type: str = "lease",
        legal_references: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        계약서 분석 실행

        Args:
            contract_text: 계약서 전문
            contract_type: 계약 유형 (lease/sale)
            legal_references: 관련 법률 조항 (선택적)

        Returns:
            분석 결과 딕셔너리
        """
        try:
            logger.info(f"Analyzing {contract_type} contract")

            # 1. 법률 조항 검색 (제공되지 않은 경우)
            if not legal_references and self.legal_search_tool:
                legal_references = await self._search_legal_references(
                    contract_text, contract_type
                )

            # 2. 기본 구조 분석
            structure_analysis = self._analyze_structure(contract_text)

            # 3. 위험 요소 탐지
            risk_analysis = self._detect_risks(contract_text, legal_references)

            # 4. 법적 준수 확인
            compliance = self._check_legal_compliance(
                contract_text, contract_type, legal_references
            )

            # 5. 개선 제안
            recommendations = self._generate_recommendations(
                structure_analysis, risk_analysis, compliance
            )

            # 6. LLM 상세 분석 (가능한 경우)
            detailed_analysis = None
            if self.llm_service:
                detailed_analysis = await self._llm_analysis(
                    contract_text, legal_references
                )

            return {
                "status": "success",
                "contract_type": contract_type,
                "structure": structure_analysis,
                "risks": risk_analysis,
                "compliance": compliance,
                "recommendations": recommendations,
                "detailed_analysis": detailed_analysis,
                "confidence": self._calculate_confidence(risk_analysis),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Contract analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "contract_type": contract_type,
                "timestamp": datetime.now().isoformat()
            }

    async def _search_legal_references(
        self,
        contract_text: str,
        contract_type: str
    ) -> List[Dict]:
        """법률 조항 검색"""
        try:
            if contract_type == "lease":
                search_query = "주택임대차보호법 임차인 보호 계약 갱신"
            else:
                search_query = "부동산 매매 계약 소유권 이전"

            results = await self.legal_search_tool.search(
                query=search_query,
                doc_type="law",
                limit=10
            )

            return results.get("results", [])
        except Exception as e:
            logger.error(f"Legal search failed: {e}")
            return []

    def _analyze_structure(self, contract_text: str) -> Dict[str, Any]:
        """계약서 구조 분석"""
        structure = {
            "has_essential_clauses": {},
            "missing_clauses": [],
            "special_terms_count": 0,
            "total_clauses": 0
        }

        # 필수 조항 확인
        for clause in self.key_clauses:
            if clause in contract_text:
                structure["has_essential_clauses"][clause] = True
            else:
                structure["missing_clauses"].append(clause)

        # 특약사항 카운트
        if "특약" in contract_text:
            # 간단한 카운팅 (실제로는 더 정교한 파싱 필요)
            structure["special_terms_count"] = contract_text.count("특약")

        structure["total_clauses"] = len(structure["has_essential_clauses"])

        return structure

    def _detect_risks(
        self,
        contract_text: str,
        legal_references: Optional[List[Dict]]
    ) -> List[Dict]:
        """위험 요소 탐지"""
        risks = []

        # 위험 키워드 검색
        for keyword in self.risk_keywords:
            if keyword in contract_text:
                # 키워드 주변 컨텍스트 추출
                index = contract_text.find(keyword)
                start = max(0, index - 50)
                end = min(len(contract_text), index + 100)
                context = contract_text[start:end]

                risks.append({
                    "type": "risky_clause",
                    "keyword": keyword,
                    "context": context.strip(),
                    "severity": self._calculate_severity(keyword),
                    "suggestion": self._get_risk_suggestion(keyword)
                })

        # 과도한 위약금 체크
        if "위약금" in contract_text:
            # 위약금 비율 체크 (간단한 패턴 매칭)
            import re
            percentages = re.findall(r'(\d+)%', contract_text)
            for pct in percentages:
                if int(pct) > 10:  # 10% 초과시 위험
                    risks.append({
                        "type": "excessive_penalty",
                        "value": f"{pct}%",
                        "severity": "high",
                        "suggestion": "위약금은 통상 계약금의 10% 이내가 적정합니다."
                    })

        return risks

    def _check_legal_compliance(
        self,
        contract_text: str,
        contract_type: str,
        legal_references: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """법적 준수 여부 확인"""
        compliance = {
            "is_compliant": True,
            "violations": [],
            "warnings": [],
            "verified_clauses": []
        }

        if contract_type == "lease":
            # 임대차보호법 준수 확인

            # 보증금 증액 제한 (5%)
            if "증액" in contract_text or "인상" in contract_text:
                import re
                percentages = re.findall(r'(\d+)%', contract_text)
                for pct in percentages:
                    if int(pct) > 5:
                        compliance["violations"].append({
                            "law": "주택임대차보호법 제7조",
                            "clause": "보증금 증액 제한",
                            "detail": f"{pct}% 증액은 법정 상한(5%)을 초과합니다."
                        })
                        compliance["is_compliant"] = False

            # 계약 갱신 요구권
            if "갱신" in contract_text and "거절" in contract_text:
                compliance["warnings"].append({
                    "law": "주택임대차보호법 제6조",
                    "clause": "계약갱신요구권",
                    "detail": "임차인의 갱신요구권을 제한하는 조항은 무효입니다."
                })

            # 2년 미만 계약
            import re
            duration = re.findall(r'(\d+)개월|(\d+)년', contract_text)
            for months, years in duration:
                if months and int(months) < 24:
                    compliance["warnings"].append({
                        "law": "주택임대차보호법 제4조",
                        "clause": "최단 임대기간",
                        "detail": f"{months}개월 계약은 법정 최단기간(2년) 미만입니다. 임차인이 원할 경우 2년으로 연장됩니다."
                    })
                elif years and int(years) < 2:
                    compliance["warnings"].append({
                        "law": "주택임대차보호법 제4조",
                        "clause": "최단 임대기간",
                        "detail": f"{years}년 계약은 법정 최단기간(2년) 미만입니다."
                    })

        return compliance

    def _generate_recommendations(
        self,
        structure: Dict,
        risks: List[Dict],
        compliance: Dict
    ) -> List[Dict]:
        """개선 제안 생성"""
        recommendations = []

        # 구조적 개선
        if structure["missing_clauses"]:
            recommendations.append({
                "category": "structure",
                "priority": "high",
                "title": "누락된 필수 조항 추가",
                "detail": f"다음 조항을 추가하세요: {', '.join(structure['missing_clauses'][:3])}",
                "action": "계약서에 누락된 필수 조항을 명시적으로 추가"
            })

        # 위험 요소 개선
        high_risks = [r for r in risks if r.get("severity") == "high"]
        if high_risks:
            recommendations.append({
                "category": "risk",
                "priority": "high",
                "title": "고위험 조항 수정 필요",
                "detail": f"{len(high_risks)}개의 고위험 조항이 발견되었습니다.",
                "action": "법률 전문가와 상담하여 조항 수정"
            })

        # 법적 준수 개선
        if compliance["violations"]:
            recommendations.append({
                "category": "compliance",
                "priority": "critical",
                "title": "법률 위반 조항 수정",
                "detail": compliance["violations"][0]["detail"],
                "action": "해당 조항을 법률에 맞게 즉시 수정"
            })

        # 일반 개선사항
        recommendations.append({
            "category": "general",
            "priority": "medium",
            "title": "확정일자 및 전입신고",
            "detail": "계약 후 즉시 확정일자를 받고 전입신고를 하세요.",
            "action": "주민센터 방문하여 확정일자 날인"
        })

        return recommendations

    async def _llm_analysis(
        self,
        contract_text: str,
        legal_references: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """LLM을 통한 상세 분석"""
        if not self.llm_service:
            return None

        try:
            prompt = f"""다음 계약서를 분석하여 주요 이슈를 찾아주세요:

계약서 내용:
{contract_text[:2000]}...

관련 법률:
{str(legal_references)[:1000] if legal_references else '없음'}

다음 항목을 중점적으로 분석해주세요:
1. 임차인에게 불리한 조항
2. 법적으로 문제가 될 수 있는 조항
3. 명확히 해야 할 애매한 표현
4. 추가로 넣으면 좋을 보호 조항
"""

            response = await self.llm_service.complete_async(
                prompt_name="contract_analysis",
                variables={"prompt": prompt},
                temperature=0.3
            )

            return {
                "llm_analysis": response,
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    def _calculate_severity(self, keyword: str) -> str:
        """위험도 계산"""
        high_risk = ["포기", "책임지지 않", "청구할 수 없"]
        medium_risk = ["일방적", "즉시", "무조건"]

        if keyword in high_risk:
            return "high"
        elif keyword in medium_risk:
            return "medium"
        else:
            return "low"

    def _get_risk_suggestion(self, keyword: str) -> str:
        """위험 요소에 대한 제안"""
        suggestions = {
            "포기": "권리 포기 조항은 무효일 수 있습니다. 삭제를 요구하세요.",
            "일방적": "상호 협의 조항으로 수정을 요청하세요.",
            "즉시": "합리적인 기간(예: 7일)으로 수정하세요.",
            "책임지지 않": "임대인의 책임 회피 조항은 제한적으로만 유효합니다."
        }

        return suggestions.get(keyword, "법률 전문가의 검토를 받으세요.")

    def _calculate_confidence(self, risks: List[Dict]) -> float:
        """분석 신뢰도 계산"""
        if not risks:
            return 0.95

        high_risks = len([r for r in risks if r.get("severity") == "high"])
        total_risks = len(risks)

        if high_risks > 3:
            return 0.60
        elif total_risks > 5:
            return 0.75
        else:
            return 0.85


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_contract_analysis():
        tool = ContractAnalysisTool()

        # 테스트 계약서
        sample_contract = """
        임대차계약서

        임대인: 홍길동
        임차인: 김철수

        1. 목적물: 서울시 강남구 역삼동 123-45 아파트 101동 1001호
        2. 보증금: 5억원
        3. 계약기간: 2024년 1월 1일 ~ 2024년 12월 31일 (12개월)
        4. 특약사항:
           - 계약기간 중 어떠한 경우에도 중도해지 불가
           - 임차인은 어떤 하자에 대해서도 임대인에게 수리를 요구할 수 없음
           - 계약 갱신시 보증금 10% 인상
           - 위약시 보증금의 50%를 위약금으로 지급
        """

        result = await tool.execute(
            contract_text=sample_contract,
            contract_type="lease"
        )

        print("=== Contract Analysis Result ===")
        print(f"Status: {result['status']}")
        print(f"Risks found: {len(result.get('risks', []))}")
        print(f"Compliance issues: {len(result.get('compliance', {}).get('violations', []))}")
        print(f"Recommendations: {len(result.get('recommendations', []))}")

        for risk in result.get('risks', [])[:3]:
            print(f"\nRisk: {risk.get('keyword')} - Severity: {risk.get('severity')}")
            print(f"  Suggestion: {risk.get('suggestion')}")

    asyncio.run(test_contract_analysis())