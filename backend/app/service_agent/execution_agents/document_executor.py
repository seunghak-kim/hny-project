"""
Document Executor - 문서 생성 및 검토 실행 Agent
문서 생성 → 검토 파이프라인을 실행
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.separated_states import (
    DocumentTeamState,
    DocumentTemplate,
    DocumentContent,
    ReviewResult,
    SharedState
)
from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class DocumentExecutor:
    """
    문서 실행 Agent
    문서 생성-검토 파이프라인 실행
    """

    def __init__(self, llm_context=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
        """
        self.llm_context = llm_context
        self.team_name = "document"

        # Agent 초기화
        self.available_agents = self._initialize_agents()

        # 문서 템플릿
        self.templates = self._load_templates()

        # Tools 초기화
        self.tools = self._initialize_tools()

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _initialize_agents(self) -> Dict[str, bool]:
        """사용 가능한 Agent 확인"""
        agent_types = ["document_agent", "review_agent"]
        available = {}

        for agent_name in agent_types:
            available[agent_name] = agent_name in AgentRegistry.list_agents(enabled_only=True)

        logger.info(f"DocumentTeam available agents: {available}")
        return available

    def _initialize_tools(self) -> Dict:
        """문서 생성 Tools 초기화"""
        tools = {}

        try:
            from app.service_agent.tools.lease_contract_generator_tool import LeaseContractGeneratorTool
            tools["lease_contract_generator"] = LeaseContractGeneratorTool()
            logger.info("LeaseContractGeneratorTool loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load LeaseContractGeneratorTool: {e}")

        return tools

    def _load_templates(self) -> Dict[str, DocumentTemplate]:
        """문서 템플릿 로드"""
        templates = {
            "lease_contract": DocumentTemplate(
                template_id="lease_001",
                template_name="주택임대차계약서",
                template_type="lease_contract",
                required_fields=["lessor", "lessee", "address", "deposit", "monthly_rent", "period"],
                optional_fields=["special_terms", "utilities", "maintenance"]
            ),
            "sales_contract": DocumentTemplate(
                template_id="sales_001",
                template_name="부동산매매계약서",
                template_type="sales_contract",
                required_fields=["seller", "buyer", "address", "price", "down_payment", "closing_date"],
                optional_fields=["mortgage", "special_terms", "broker"]
            ),
            "loan_application": DocumentTemplate(
                template_id="loan_001",
                template_name="대출신청서",
                template_type="loan_application",
                required_fields=["applicant", "amount", "purpose", "income", "collateral"],
                optional_fields=["co_signer", "existing_loans"]
            )
        }
        return templates

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(DocumentTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_document_node)
        workflow.add_node("generate", self.generate_document_node)
        workflow.add_node("review_check", self.review_check_node)
        workflow.add_node("review", self.review_document_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START, "prepare")
        workflow.add_edge("prepare", "generate")
        workflow.add_edge("generate", "review_check")

        # 검토 필요 여부 확인
        workflow.add_conditional_edges(
            "review_check",
            self._needs_review,
            {
                "review": "review",
                "skip": "finalize"
            }
        )

        workflow.add_edge("review", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("DocumentTeam subgraph built successfully")

    def _needs_review(self, state: DocumentTeamState) -> str:
        """검토 필요 여부 결정"""
        if state.get("review_requested", True):
            return "review"
        return "skip"

    async def prepare_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
        """
        문서 준비 노드
        템플릿 선택 및 파라미터 검증
        """
        logger.info("[DocumentTeam] Preparing document")

        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()

        # 문서 타입 확인
        doc_type = state.get("document_type", "lease_contract")

        # 템플릿 선택
        template = self.templates.get(doc_type)
        if template:
            state["template"] = template
            logger.info(f"[DocumentTeam] Selected template: {template['template_name']}")
        else:
            logger.warning(f"[DocumentTeam] Template not found for: {doc_type}")
            state["template"] = self.templates["lease_contract"]  # 기본 템플릿

        # 파라미터 검증
        if not state.get("document_params"):
            state["document_params"] = self._extract_params_from_context(state)

        state["generation_status"] = "ready"
        return state

    def _extract_params_from_context(self, state: DocumentTeamState) -> Dict[str, Any]:
        """컨텍스트에서 문서 파라미터 추출"""
        shared_context = state.get("shared_context", {})
        query = shared_context.get("query", "")

        # 간단한 파라미터 추출 (실제로는 NLP 사용)
        params = {
            "generated_at": datetime.now().isoformat(),
            "query": query
        }

        # 숫자 추출
        import re
        numbers = re.findall(r'\d+[억만원]?', query)
        if numbers:
            params["amount"] = numbers[0]

        return params

    async def generate_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
        """
        문서 생성 노드
        DocumentAgent 또는 Tool 호출
        """
        logger.info("[DocumentTeam] Generating document")

        state["generation_status"] = "in_progress"
        doc_type = state.get("document_type", "lease_contract")

        # 주택임대차 계약서는 Tool 사용
        if doc_type == "lease_contract" and "lease_contract_generator" in self.tools:
            try:
                tool = self.tools["lease_contract_generator"]
                params = state.get("document_params", {})

                result = await tool.execute(**params)

                if result.get("status") == "success":
                    # 문서 내용 저장
                    state["generated_document"] = DocumentContent(
                        title=result.get("title", "주택임대차 표준계약서"),
                        sections=result.get("sections", []),
                        metadata=result.get("metadata", {}),
                        generated_at=datetime.now()
                    )
                    state["draft_content"] = result.get("content", "")
                    state["generation_status"] = "completed"
                elif result.get("error_type") == "template_not_loaded":
                    # 템플릿 로드 실패 - 사용자에게 안내
                    state["generation_status"] = "failed"
                    state["error"] = result.get("message")
                else:
                    state["generation_status"] = "failed"
                    state["error"] = result.get("error", "Document generation failed")

                return state

            except Exception as e:
                logger.error(f"Tool-based document generation failed: {e}")
                # Tool 실패시 기존 방식으로 fallback

        # DocumentAgent 사용
        if not self.available_agents.get("document_agent"):
            # DocumentAgent가 없으면 모의 생성
            state["generated_document"] = self._mock_generate_document(state)
            state["generation_status"] = "completed"
            return state

        # DocumentAgent 입력 준비
        doc_input = {
            "document_type": state.get("document_type", "lease_contract"),
            "document_params": state.get("document_params", {}),
            "template": state.get("template"),
            "query": state.get("shared_context", {}).get("query", ""),
            "original_query": state.get("shared_context", {}).get("original_query", ""),
            "chat_session_id": state.get("shared_context", {}).get("session_id", "")
        }

        try:
            # DocumentAgent 실행
            result = await AgentAdapter.execute_agent_dynamic(
                "document_agent",
                doc_input,
                self.llm_context
            )

            if result.get("status") in ["completed", "success"]:
                data = result.get("data", {})

                # 문서 내용 저장
                state["generated_document"] = DocumentContent(
                    title=data.get("title", "생성된 문서"),
                    sections=data.get("sections", []),
                    metadata=data.get("metadata", {}),
                    generated_at=datetime.now()
                )

                state["draft_content"] = data.get("content", "")
                state["generation_status"] = "completed"
            else:
                state["generation_status"] = "failed"
                state["error"] = result.get("error", "Document generation failed")

        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            state["generation_status"] = "failed"
            state["error"] = str(e)

        return state

    def _mock_generate_document(self, state: DocumentTeamState) -> DocumentContent:
        """모의 문서 생성 (테스트용)"""
        template = state.get("template", {})

        return DocumentContent(
            title=template.get("template_name", "문서"),
            sections=[
                {
                    "title": "계약 당사자",
                    "content": "임대인: [임대인명]\n임차인: [임차인명]"
                },
                {
                    "title": "목적물",
                    "content": "주소: [주소]\n면적: [면적]"
                },
                {
                    "title": "계약 조건",
                    "content": "보증금: [금액]\n월세: [금액]\n계약기간: [기간]"
                }
            ],
            metadata={
                "template_id": template.get("template_id", ""),
                "generated_by": "DocumentTeam"
            },
            generated_at=datetime.now()
        )

    async def review_check_node(self, state: DocumentTeamState) -> DocumentTeamState:
        """
        검토 확인 노드
        검토 필요 여부 결정
        """
        logger.info("[DocumentTeam] Checking if review is needed")

        # 기본적으로 검토 수행
        if state.get("generation_status") == "completed":
            state["review_requested"] = True
            state["review_status"] = "pending"
        else:
            state["review_requested"] = False

        return state

    async def review_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
        """
        문서 검토 노드
        ReviewAgent 호출
        """
        logger.info("[DocumentTeam] Reviewing document")

        state["review_status"] = "in_progress"

        if not self.available_agents.get("review_agent"):
            # ReviewAgent가 없으면 모의 검토
            state["review_result"] = self._mock_review_document(state)
            state["review_status"] = "completed"
            return state

        # ReviewAgent 입력 준비
        review_input = {
            "document_content": state.get("draft_content", ""),
            "document_type": state.get("document_type", ""),
            "review_type": "comprehensive",
            "query": state.get("shared_context", {}).get("query", ""),
            "chat_session_id": state.get("shared_context", {}).get("session_id", "")
        }

        try:
            # ReviewAgent 실행
            result = await AgentAdapter.execute_agent_dynamic(
                "review_agent",
                review_input,
                self.llm_context
            )

            if result.get("status") in ["completed", "success"]:
                data = result.get("data", {})

                # 검토 결과 저장
                state["review_result"] = ReviewResult(
                    risk_level=data.get("risk_level", "low"),
                    risk_factors=data.get("risk_factors", []),
                    recommendations=data.get("recommendations", []),
                    compliance_check=data.get("compliance_check", {}),
                    score=data.get("score", 0.8)
                )

                state["review_status"] = "completed"
            else:
                state["review_status"] = "failed"
                state["error"] = result.get("error", "Review failed")

        except Exception as e:
            logger.error(f"Document review failed: {e}")
            state["review_status"] = "failed"
            state["error"] = str(e)

        return state

    def _mock_review_document(self, state: DocumentTeamState) -> ReviewResult:
        """모의 문서 검토 (테스트용)"""
        return ReviewResult(
            risk_level="low",
            risk_factors=["필수 항목 누락 가능성"],
            recommendations=["계약 기간 명시 필요", "특약사항 추가 검토"],
            compliance_check={
                "법적요건": True,
                "필수항목": True,
                "형식요건": True
            },
            score=0.85
        )

    async def finalize_node(self, state: DocumentTeamState) -> DocumentTeamState:
        """
        최종화 노드
        최종 문서 생성 및 상태 정리
        """
        logger.info("[DocumentTeam] Finalizing")

        # 최종 문서 생성
        if state.get("generated_document"):
            # 검토 결과 반영
            if state.get("review_result"):
                review = state["review_result"]
                metadata = {
                    "risk_level": review.get("risk_level"),
                    "review_score": review.get("score"),
                    "reviewed": True
                }
            else:
                metadata = {"reviewed": False}

            # 최종 문서 포맷팅
            state["final_document"] = self._format_final_document(
                state["generated_document"],
                metadata
            )

            state["document_format"] = "markdown"  # 기본 포맷

        # 메타데이터 정리
        state["document_metadata"] = {
            "document_type": state.get("document_type"),
            "template_used": state.get("template", {}).get("template_id"),
            "generated_at": state.get("start_time"),
            "reviewed": state.get("review_status") == "completed",
            "review_score": state.get("review_result", {}).get("score") if state.get("review_result") else None
        }

        state["end_time"] = datetime.now()

        # 상태 결정
        if state.get("error"):
            state["status"] = "failed"
        elif state.get("final_document"):
            state["status"] = "completed"
        else:
            state["status"] = "partial"

        logger.info(f"[DocumentTeam] Completed with status: {state['status']}")
        return state

    def _format_final_document(self, document: DocumentContent, metadata: Dict) -> str:
        """최종 문서 포맷팅"""
        lines = [f"# {document['title']}\n"]

        # 메타데이터
        lines.append(f"*생성일시: {document.get('generated_at', datetime.now())}*\n")

        if metadata.get("reviewed"):
            lines.append(f"*검토 완료 (위험도: {metadata.get('risk_level', 'N/A')})*\n")

        lines.append("\n---\n")

        # 섹션들
        for section in document.get("sections", []):
            lines.append(f"\n## {section.get('title', '섹션')}\n")
            lines.append(f"{section.get('content', '')}\n")

        return "\n".join(lines)

    async def execute(
        self,
        shared_state: SharedState,
        document_type: str = "lease_contract",
        document_params: Optional[Dict] = None,
        review_requested: bool = True
    ) -> DocumentTeamState:
        """
        DocumentTeam 실행

        Args:
            shared_state: 공유 상태
            document_type: 문서 타입
            document_params: 문서 파라미터
            review_requested: 검토 요청 여부

        Returns:
            문서 팀 상태
        """
        # 초기 상태 생성
        initial_state = DocumentTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            document_type=document_type,
            document_params=document_params or {},
            template=None,
            generation_status="",
            draft_content=None,
            generated_document=None,
            review_requested=review_requested,
            review_status=None,
            review_result=None,
            final_document=None,
            document_format="markdown",
            document_metadata={},
            start_time=None,
            end_time=None,
            error=None
        )

        # 서브그래프 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"DocumentTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state


# 테스트 코드
if __name__ == "__main__":
    async def test_document_team():
        from app.service_agent.foundation.separated_states import StateManager

        # DocumentTeam 초기화
        doc_team = DocumentTeamSupervisor()

        # 테스트 케이스
        test_cases = [
            ("lease_contract", {"deposit": "1억", "monthly": "100만원"}),
            ("sales_contract", {"price": "10억"}),
            ("loan_application", {"amount": "5억"})
        ]

        for doc_type, params in test_cases:
            print(f"\n{'='*60}")
            print(f"Document Type: {doc_type}")
            print(f"Parameters: {params}")
            print("-"*60)

            # 공유 상태 생성
            shared_state = StateManager.create_shared_state(
                query=f"{doc_type} 작성해주세요",
                session_id="test_doc_team"
            )

            # DocumentTeam 실행
            result = await doc_team.execute(
                shared_state,
                document_type=doc_type,
                document_params=params
            )

            print(f"Status: {result['status']}")
            print(f"Generation: {result.get('generation_status')}")
            print(f"Review: {result.get('review_status')}")

            if result.get("review_result"):
                review = result["review_result"]
                print(f"Risk Level: {review.get('risk_level')}")
                print(f"Score: {review.get('score')}")

            if result.get("final_document"):
                print("\n[Final Document Preview]")
                print(result["final_document"][:200] + "...")

    import asyncio
    asyncio.run(test_document_team())