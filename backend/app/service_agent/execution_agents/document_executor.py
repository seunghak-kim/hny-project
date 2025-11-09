"""
Document Executor - Consolidated Document Team Implementation

Generates documents with Human-In-The-Loop (HITL) approval using LangGraph 0.6.

This executor consolidates the previous document_team implementation into a single
class-based executor. It implements a streamlined workflow:

    Planning → Aggregate (HITL) → Generate

Key Features:
- LangGraph 0.6 interrupt() for HITL approval
- Mock implementation for testing (TODO: Add real LLM integration)
- Designed for future tool integration (ValidationTool, ComplianceTool)
- Uses MainSupervisorState for parent graph integration

Author: Holmes AI Team
Date: 2025-10-26
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.service_agent.foundation.separated_states import MainSupervisorState
from app.service_agent.llm_manager.llm_service import LLMService
from app.service_agent.tools.lease_contract_generator_tool import LeaseContractGeneratorTool

logger = logging.getLogger(__name__)


class DocumentExecutor:
    """
    Document generation executor with HITL workflow.

    Workflow:
    1. Planning: Analyze query and determine document requirements
    2. Aggregate: Consolidate information and request HITL approval
    3. Generate: Create final document based on approved content

    Attributes:
        llm_context: LLM context for future integration (currently unused)
        checkpointer: PostgreSQL checkpointer for state persistence
    """

    def __init__(self, llm_context=None, checkpointer=None, progress_callback=None):
        """
        Initialize DocumentExecutor.

        Args:
            llm_context: Optional LLM context for future integration
            checkpointer: AsyncPostgresSaver for state checkpointing
            progress_callback: Optional callback for real-time progress updates
        """
        self.llm_context = llm_context
        self.checkpointer = checkpointer
        self.progress_callback = progress_callback  # 🆕 Store parent's WebSocket callback

        # ✅ Initialize LLM Service for information extraction
        self.llm_service = LLMService(llm_context=llm_context)

        # ✅ Initialize LeaseContractGeneratorTool for DOCX generation
        self.contract_tool = LeaseContractGeneratorTool()

        logger.info("📄 DocumentExecutor initialized with LLM and contract generation tool")

    def build_workflow(self):
        """
        Build the document generation workflow graph.

        Workflow Structure:
            START → planning → aggregate (HITL) → generate → END

        Returns:
            Compiled StateGraph with interrupt support
        """
        logger.info("🔧 Building document generation workflow")

        workflow = StateGraph(MainSupervisorState)

        # Add nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("generate", self.generate_node)

        # Define edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "aggregate")
        workflow.add_edge("aggregate", "generate")
        workflow.add_edge("generate", END)

        # Compile with checkpointer for HITL support
        compiled_graph = workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=[]  # interrupt() is called within aggregate_node
        )

        logger.info("✅ Document workflow compiled successfully")
        return compiled_graph

    # ==================== Node Methods ====================

    async def planning_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Planning Node: Extract lease contract information from user conversation.

        Uses LLM to intelligently extract all contract fields from natural language.

        Implementation:
        - Uses LLM to analyze conversation history
        - Extracts structured contract information (15 fields)
        - Normalizes dates and amounts
        - Returns extracted fields with null for missing data

        Args:
            state: MainSupervisorState containing query and conversation history

        Returns:
            Updated state with extracted_fields and planning_result
        """
        logger.info("📋 Planning node: Extracting lease contract information with LLM")

        # 🆕 Step Progress: Step 1 (정보 추출) - Start
        await self._update_step_progress(state, step_index=0, status="in_progress", progress=0)

        query = state.get("query", "")
        conversation_history = state.get("conversation_history", [])

        # Build conversation context for LLM
        conversation_text = self._build_conversation_context(conversation_history, query)

        logger.info(f"Extracting contract info from conversation ({len(conversation_text)} chars)")

        try:
            # ✅ Call LLM to extract contract information
            response = await self.llm_service.complete_async(
                prompt_name="lease_contract_extraction",
                variables={
                    "conversation_history": conversation_text,
                    "query": query
                },
                model="gpt-4o",  # Use more capable model for extraction
                temperature=0.1,  # Low temperature for accuracy
                response_format={"type": "json_object"}
            )

            # 🔍 Debug: Log FULL LLM response for diagnosis
            logger.info(f"🔍 Full LLM response ({len(response)} chars): {response[:1000]}")

            # Parse JSON response
            extracted_fields = json.loads(response)

            # 🔍 Debug: Log extracted fields for diagnosis
            non_null_count = len([v for v in extracted_fields.values() if v is not None])
            non_empty_count = len([v for v in extracted_fields.values() if v and (not isinstance(v, str) or v.strip())])

            logger.info(f"✅ LLM extraction complete: {non_null_count} non-null fields, {non_empty_count} non-empty fields")
            logger.info(f"📋 Extracted ALL fields: {json.dumps(extracted_fields, ensure_ascii=False, indent=2)}")

            # Create planning result
            planning_result = {
                "document_type": "lease_contract",
                "extracted_fields": extracted_fields,
                "extraction_method": "llm",
                "timestamp": datetime.now().isoformat()
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Response was: {response[:500]}")

            # Fallback: empty fields
            extracted_fields = self._get_empty_contract_fields()
            planning_result = {
                "document_type": "lease_contract",
                "extracted_fields": extracted_fields,
                "extraction_method": "fallback",
                "error": f"JSON parsing failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

            # Fallback: empty fields
            extracted_fields = self._get_empty_contract_fields()
            planning_result = {
                "document_type": "lease_contract",
                "extracted_fields": extracted_fields,
                "extraction_method": "fallback",
                "error": f"LLM call failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

        logger.info(f"Planning complete: {planning_result['document_type']} document")

        # 🆕 Step Progress: Step 1 (정보 추출) - Complete
        await self._update_step_progress(state, step_index=0, status="completed", progress=100)

        return {
            "planning_result": planning_result,
            "extracted_fields": extracted_fields,
            "workflow_status": "running"
        }

    async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Aggregate Node: Validate extracted fields and request HITL approval.

        This is the CRITICAL HITL node using LangGraph 0.6 interrupt() pattern.

        Workflow:
        1. Get extracted fields from planning_result
        2. Check for missing required fields (ALL 15 fields are required)
        3. Generate Markdown preview
        4. Call interrupt() to request user confirmation
        5. Resume when parent graph calls Command(resume=user_feedback)
        6. Apply user modifications if action == "modify"

        HITL Pattern (LangGraph 0.6):
        - Uses interrupt() function (NOT NodeInterrupt exception)
        - interrupt() stores value in checkpoint and waits
        - Parent graph retrieves via get_state().tasks[0].interrupts[0]
        - Resume with Command(resume=value)

        Args:
            state: MainSupervisorState containing extracted_fields

        Returns:
            Updated state with validated_fields and collaboration_result
        """
        logger.info("📊 Aggregate node: Validating extracted contract fields")

        # 🆕 Step Progress: Step 2 (필드 검증) - Start
        await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)

        # Get extracted fields
        extracted_fields = state.get("extracted_fields", {})
        if not extracted_fields:
            extracted_fields = self._get_empty_contract_fields()

        # ✅ Check for missing required fields (ALL 15 fields)
        missing_fields = self._check_required_fields(extracted_fields)

        logger.info(f"Field validation: {len(missing_fields)} required fields missing (out of 6 required)")
        if missing_fields:
            logger.info(f"⚠️  Missing required fields: {', '.join(missing_fields)}")

        # Generate Markdown preview
        markdown_preview = self._generate_markdown_preview(extracted_fields, missing_fields)

        # 🆕 Step Progress: Step 2 (필드 검증) - Complete
        await self._update_step_progress(state, step_index=1, status="completed", progress=100)

        # 🆕 Step Progress: Step 3 (정보 확인 HITL) - Start
        await self._update_step_progress(state, step_index=2, status="in_progress", progress=0)

        logger.info("⏸️  Requesting human confirmation via interrupt()")

        # Build user-friendly message
        if missing_fields:
            # ✅ Get field labels from Python config
            prompt_config = self.llm_service.prompt_manager.get_prompt_config("lease_contract_extraction")

            if prompt_config:
                field_labels = prompt_config.field_labels
                logger.debug(f"Using field labels from Python config ({len(field_labels)} labels)")
            else:
                # Fallback: hardcoded labels
                field_labels = {
                    "address_road": "도로명주소",
                    "address_detail": "상세주소",
                    "deposit": "보증금",
                    "monthly_rent": "월세",
                    "start_date": "계약 시작일",
                    "end_date": "계약 종료일",
                    "lessor_name": "임대인 성명",
                    "lessee_name": "임차인 성명",
                    "lessor_phone": "임대인 전화번호",
                    "lessee_phone": "임차인 전화번호",
                    "lessor_address": "임대인 주소",
                    "lessee_address": "임차인 주소",
                    "management_fee": "관리비",
                    "special_terms": "특약사항",
                    "contract_payment": "계약금"
                }
                logger.debug("Using fallback hardcoded field labels")

            missing_labels = [field_labels.get(f, f) for f in missing_fields]
            message = f"다음 {len(missing_fields)}개 항목이 누락되었습니다:\n" + "\n".join([f"- {label}" for label in missing_labels])
        else:
            message = "모든 필드가 입력되었습니다. 내용을 확인해주세요."

        # Prepare interrupt value with user-facing data and metadata
        interrupt_value = {
            # User-facing data
            "aggregated_content": markdown_preview,
            "missing_fields": missing_fields,
            "extracted_count": len([v for v in extracted_fields.values() if v is not None]),
            "total_fields": 20,
            "required_fields": 6,
            "message": message,
            "options": {
                "approve": "확인 및 계속 진행",
                "modify": "내용 수정",
                "reject": "취소"
            },
            # Metadata for parent graph
            "_metadata": {
                "interrupted_by": "document_aggregate",
                "interrupt_type": "approval",
                "node_name": "document.aggregate"
            }
        }

        # Update state before interrupt
        state["aggregated_content"] = markdown_preview
        state["validated_fields"] = extracted_fields
        state["missing_fields"] = missing_fields
        state["workflow_status"] = "interrupted"

        # ✅ LangGraph 0.6 HITL Pattern: Use interrupt() function
        # Execution pauses here until Command(resume=...) is called
        user_feedback = interrupt(interrupt_value)

        # 🔄 Execution resumes here after Command(resume=user_feedback)
        logger.info("▶️  Workflow resumed with user feedback")
        logger.info(f"User feedback action: {user_feedback.get('action') if user_feedback else 'None'}")

        # 🆕 Step Progress: Step 3 (정보 확인 HITL) - Complete
        await self._update_step_progress(state, step_index=2, status="completed", progress=100)

        # 🆕 Step Progress: Step 4 (필드 업데이트) - Start
        await self._update_step_progress(state, step_index=3, status="in_progress", progress=0)

        # Process user feedback
        validated_fields = extracted_fields.copy()

        if user_feedback and user_feedback.get("action") == "modify":
            logger.info("Applying user modifications to contract fields")

            # Apply modifications (missing_fields values from feedback)
            if "missing_fields" in user_feedback:
                for field_name, value in user_feedback["missing_fields"].items():
                    if value:
                        validated_fields[field_name] = value
                        logger.info(f"Updated field '{field_name}': {value}")

            # Apply prompt-based modifications if present
            if "modifications" in user_feedback and user_feedback["modifications"]:
                logger.info("Applying prompt-based modifications")
                # TODO: Use LLM to parse natural language modifications
                # For now, just log the modifications
                logger.info(f"Modifications prompt: {user_feedback['modifications']}")

        # 🆕 Step Progress: Step 4 (필드 업데이트) - Complete
        await self._update_step_progress(state, step_index=3, status="completed", progress=100)

        return {
            "validated_fields": validated_fields,
            "aggregated_content": self._generate_markdown_preview(validated_fields, []),
            "collaboration_result": user_feedback,
            "workflow_status": "running",
            "interrupted_by": "document_aggregate",
            "interrupt_type": "approval"
        }

    async def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Generate Node: Generate DOCX lease contract using LeaseContractGeneratorTool.

        Implementation:
        - Get validated fields from state
        - Call LeaseContractGeneratorTool.execute() with all fields
        - Generate DOCX file
        - Create download URL
        - Return final response with document path and preview

        Args:
            state: MainSupervisorState containing validated_fields

        Returns:
            Updated state with final_document, final_response, team_results
        """
        logger.info("📝 Generate node: Creating DOCX lease contract")

        # 🆕 Step Progress: Step 5 (문서 생성) - Start
        await self._update_step_progress(state, step_index=4, status="in_progress", progress=0)

        # Get validated fields
        validated_fields = state.get("validated_fields", {})
        if not validated_fields:
            logger.error("No validated fields found in state")
            validated_fields = self._get_empty_contract_fields()

        logger.info(f"Generating contract with {len([v for v in validated_fields.values() if v])} filled fields")

        # ✅ Call LeaseContractGeneratorTool to generate DOCX
        try:
            generation_result = await self.contract_tool.execute(**validated_fields)

            if generation_result.get("success"):
                docx_path = generation_result.get("docx_path")
                markdown_preview = generation_result.get("markdown_summary", "")

                logger.info(f"✅ DOCX generated successfully: {docx_path}")

                # 🆕 Step Progress: Step 5 (문서 생성) - Complete
                await self._update_step_progress(state, step_index=4, status="completed", progress=100)

                # 🆕 Step Progress: Step 6 (최종 승인 HITL) - Start
                await self._update_step_progress(state, step_index=5, status="in_progress", progress=0)

                # ⏸️ Second HITL: Final review and approval
                logger.info("⏸️  Requesting final document approval via interrupt()")

                interrupt_value = {
                    "preview": markdown_preview,
                    "docx_path": docx_path,
                    "message": "계약서가 생성되었습니다. 최종 승인해주세요.",
                    "options": {
                        "approve": "최종 승인 및 다운로드",
                        "regenerate": "재생성",
                        "reject": "취소"
                    },
                    "_metadata": {
                        "interrupted_by": "document_final_review",
                        "interrupt_type": "final_approval",
                        "node_name": "document.generate"
                    }
                }

                # Update state before interrupt
                state["docx_path"] = docx_path
                state["workflow_status"] = "interrupted"

                # ✅ Second HITL: Final approval
                final_approval = interrupt(interrupt_value)

                # 🔄 Resumed after final approval
                logger.info("▶️  Workflow resumed after final approval")
                logger.info(f"Final approval action: {final_approval.get('action') if final_approval else 'None'}")

                # 🆕 Step Progress: Step 6 (최종 승인) - Complete
                await self._update_step_progress(state, step_index=5, status="completed", progress=100)

                # Build final response
                final_response = {
                    "answer": f"주택임대차 계약서가 생성되었습니다.\n\n{markdown_preview}",
                    "document_type": "lease_contract",
                    "docx_path": docx_path,
                    "docx_download_url": f"/api/v1/documents/download/{Path(docx_path).name}",
                    "markdown_preview": markdown_preview,
                    "user_approved": final_approval.get("action") == "approve" if final_approval else True,
                    "type": "document"
                }

            else:
                # Generation failed
                error_message = generation_result.get("error", "Unknown error")
                logger.error(f"❌ DOCX generation failed: {error_message}")

                await self._update_step_progress(state, step_index=4, status="failed", progress=0)

                final_response = {
                    "answer": f"계약서 생성에 실패했습니다: {error_message}",
                    "document_type": "lease_contract",
                    "error": error_message,
                    "success": False,
                    "type": "document"
                }

        except Exception as e:
            logger.error(f"❌ Exception during DOCX generation: {e}")

            await self._update_step_progress(state, step_index=4, status="failed", progress=0)

            final_response = {
                "answer": f"계약서 생성 중 오류 발생: {str(e)}",
                "document_type": "lease_contract",
                "error": str(e),
                "success": False,
                "type": "document"
            }

        logger.info(f"✅ Final response created: {final_response.get('document_type')}")

        # Add to team_results for Parent Graph aggregation
        team_results = {
            "document": {
                "status": "success" if final_response.get("success", True) else "error",
                "data": final_response
            }
        }

        logger.info("✅ Document Team results added to team_results")

        return {
            "final_document": final_response.get("markdown_preview", ""),
            "final_response": final_response,
            "workflow_status": "completed",
            "team_results": team_results
        }

    # ==================== Private Helper Methods ====================

    def _build_conversation_context(self, conversation_history: List[Dict], current_query: str) -> str:
        """
        Build conversation context text for LLM extraction.

        Args:
            conversation_history: List of conversation messages
            current_query: Current user query

        Returns:
            Formatted conversation text
        """
        if not conversation_history:
            return "이전 대화 없음"

        # Format conversation history
        context_parts = []
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                context_parts.append(f"사용자: {content}")
            elif role == "assistant":
                context_parts.append(f"AI: {content}")

        return "\n".join(context_parts)

    def _get_empty_contract_fields(self) -> Dict[str, Any]:
        """
        Get empty contract fields template.

        Returns:
            Dictionary with all 15 fields set to null
        """
        return {
            # 물건 정보
            "address_road": None,
            "address_detail": None,
            "land_area": None,
            "building_area": None,
            "rental_area": None,
            # 금액 정보
            "deposit": None,
            "deposit_hangeul": None,
            "contract_payment": None,
            "monthly_rent": None,
            "monthly_rent_day": None,
            "management_fee": None,
            # 기간 정보
            "start_date": None,
            "end_date": None,
            # 당사자 정보
            "lessor_name": None,
            "lessor_address": None,
            "lessor_phone": None,
            "lessee_name": None,
            "lessee_address": None,
            "lessee_phone": None,
            # 특약사항
            "special_terms": None
        }

    def _check_required_fields(self, fields: Dict[str, Any]) -> List[str]:
        """
        Check for missing required fields.

        Uses Python prompt config for field definitions (v2.0.0+).
        Fallback: hardcoded list if config not available.

        Args:
            fields: Dictionary of extracted contract fields

        Returns:
            List of missing field names
        """
        # ✅ Get required fields from Python prompt config
        prompt_config = self.llm_service.prompt_manager.get_prompt_config("lease_contract_extraction")

        if prompt_config:
            required_fields = prompt_config.required_fields
            logger.debug(f"Using required fields from Python config ({len(required_fields)} fields)")
        else:
            # Fallback: hardcoded list
            required_fields = [
                "address_road",
                "deposit",
                "start_date",
                "end_date",
                "lessor_name",
                "lessee_name"
            ]
            logger.debug("Using fallback hardcoded required fields")

        missing = []
        for field_name in required_fields:
            value = fields.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field_name)

        return missing

    def _generate_markdown_preview(self, fields: Dict[str, Any], missing_fields: List[str]) -> str:
        """
        Generate Markdown preview of contract fields.

        Args:
            fields: Dictionary of contract fields
            missing_fields: List of missing field names

        Returns:
            Markdown formatted string
        """
        def format_field(label: str, value: Any, field_name: str) -> str:
            """Format a single field with missing indicator"""
            if field_name in missing_fields:
                return f"- **{label}**: ⚠️ *누락*"
            elif value is None:
                return f"- **{label}**: -"
            else:
                return f"- **{label}**: {value}"

        preview = "# 주택임대차 표준계약서\n\n"

        # 물건 정보
        preview += "## 📍 물건 정보\n"
        preview += format_field("도로명주소", fields.get("address_road"), "address_road") + "\n"
        preview += format_field("상세주소", fields.get("address_detail"), "address_detail") + "\n"
        if fields.get("rental_area"):
            preview += f"- **임차 면적**: {fields['rental_area']}㎡\n"
        preview += "\n"

        # 금액 정보
        preview += "## 💰 금액 정보\n"
        preview += format_field("보증금", fields.get("deposit"), "deposit") + "\n"
        preview += format_field("월세", fields.get("monthly_rent"), "monthly_rent") + "\n"
        preview += format_field("관리비", fields.get("management_fee"), "management_fee") + "\n"
        preview += format_field("계약금", fields.get("contract_payment"), "contract_payment") + "\n"
        preview += "\n"

        # 기간 정보
        preview += "## 📅 계약 기간\n"
        preview += format_field("시작일", fields.get("start_date"), "start_date") + "\n"
        preview += format_field("종료일", fields.get("end_date"), "end_date") + "\n"
        preview += "\n"

        # 임대인 정보
        preview += "## 👤 임대인 정보\n"
        preview += format_field("성명", fields.get("lessor_name"), "lessor_name") + "\n"
        preview += format_field("주소", fields.get("lessor_address"), "lessor_address") + "\n"
        preview += format_field("전화번호", fields.get("lessor_phone"), "lessor_phone") + "\n"
        preview += "\n"

        # 임차인 정보
        preview += "## 👤 임차인 정보\n"
        preview += format_field("성명", fields.get("lessee_name"), "lessee_name") + "\n"
        preview += format_field("주소", fields.get("lessee_address"), "lessee_address") + "\n"
        preview += format_field("전화번호", fields.get("lessee_phone"), "lessee_phone") + "\n"
        preview += "\n"

        # 특약사항
        preview += "## 📝 특약사항\n"
        special_terms = fields.get("special_terms")
        if special_terms:
            preview += f"{special_terms}\n"
        else:
            if "special_terms" in missing_fields:
                preview += "⚠️ *누락*\n"
            else:
                preview += "없음\n"

        return preview

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract search keywords from user query.

        Current: Simple split (Mock)
        TODO: Use LLM for intelligent keyword extraction

        Args:
            query: User query string

        Returns:
            List of extracted keywords
        """
        # Simple extraction: take first 5 words
        keywords = query.split()[:5]
        logger.debug(f"Extracted keywords: {keywords}")
        return keywords

    def _mock_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Perform mock search for testing.

        Current: Returns fake search results
        TODO: Integrate with actual search tools:
        - Legal database search
        - Real estate database search
        - Document template search
        - Compliance guideline search

        Args:
            keywords: List of search keywords

        Returns:
            List of mock search results
        """
        search_results = []
        for keyword in keywords:
            result = {
                "keyword": keyword,
                "source": "mock_database",
                "content": f"Mock search result for: {keyword}",
                "relevance_score": 0.85,
                "timestamp": "2025-10-26T00:00:00"
            }
            search_results.append(result)

        logger.debug(f"Mock search complete: {len(search_results)} results")
        return search_results

    def _aggregate_results(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Aggregate search results into coherent content.

        Current: Simple concatenation
        TODO: Use LLM to create intelligent aggregation with:
        - Semantic clustering
        - Relevance ranking
        - Duplicate removal
        - Coherent narrative structure

        Args:
            search_results: List of search result dictionaries

        Returns:
            Aggregated content string
        """
        if not search_results:
            return "No search results to aggregate."

        # Simple aggregation
        aggregated = "\n\n".join([
            f"- {result.get('keyword', 'Unknown')}: {result.get('content', 'No content')}"
            for result in search_results
        ])

        return f"Aggregated Content:\n{aggregated}"

    def _apply_user_feedback(self, content: str, feedback: Dict[str, Any]) -> str:
        """
        Apply user feedback to modify content.

        Current: Simple append
        TODO: Use LLM to intelligently apply modifications:
        - Understand user intent
        - Merge changes coherently
        - Maintain document structure
        - Preserve important information

        Args:
            content: Original aggregated content
            feedback: User feedback dictionary

        Returns:
            Modified content string
        """
        modifications = feedback.get("modifications", "")
        if modifications:
            # Simple append for now
            return f"{content}\n\n[User Feedback Applied]\n{modifications}"
        return content

    def _format_document(
        self,
        content: str,
        planning: Dict[str, Any],
        feedback: Dict[str, Any]
    ) -> str:
        """
        Format final document with proper structure.

        Current: Simple text template
        TODO: Use LLM and templates for professional formatting:
        - Document type-specific templates (lease contract, legal notice, etc.)
        - DOCX/PDF generation
        - Legal compliance formatting
        - Professional styling

        Args:
            content: Aggregated content
            planning: Planning result dictionary
            feedback: User feedback dictionary

        Returns:
            Formatted document string
        """
        doc_type = planning.get("document_type", "general")
        sections = planning.get("sections", [])

        document = f"""
# Document: {doc_type.upper()}

## Generated Content

{content}

## Metadata
- Document Type: {doc_type}
- Sections: {', '.join(sections)}
- User Approved: {feedback.get('action') == 'approve' if feedback else False}
- Generation Time: 2025-10-26

---
Generated by Holmes AI Document Team
"""

        return document.strip()

    async def _update_step_progress(
        self,
        state: MainSupervisorState,
        step_index: int,
        status: str,
        progress: int = 0
    ) -> None:
        """
        🆕 Update agent step progress in state AND forward to WebSocket.

        This method writes step progress updates to the state and forwards
        them to the parent graph via WebSocket callback for real-time UI updates.

        Args:
            state: MainSupervisorState
            step_index: Step index (0-5 for document agent's 6 steps)
            status: Step status ("pending", "in_progress", "completed", "failed")
            progress: Progress percentage (0-100)
        """
        # Initialize document_step_progress if not exists
        if "document_step_progress" not in state:
            state["document_step_progress"] = {}

        # Update step progress in state
        state["document_step_progress"][f"step_{step_index}"] = {
            "index": step_index,
            "status": status,
            "progress": progress
        }

        logger.debug(f"[DocumentExecutor] Step {step_index} progress: {status} ({progress}%)")

        # 🆕 Forward to WebSocket via parent callback for real-time UI updates
        if self.progress_callback:
            await self.progress_callback("agent_step_progress", {
                "agentName": "document",
                "agentType": "document",
                "stepId": f"document_step_{step_index + 1}",  # 1-indexed for frontend
                "stepIndex": step_index,
                "status": status,
                "progress": progress
            })
            logger.debug(f"[DocumentExecutor] Forwarded step {step_index} progress to WebSocket")


# ==================== Public API ====================

def build_document_workflow(checkpointer):
    """
    Build and return the document generation workflow.

    This is the main entry point used by TeamSupervisor to integrate
    the document team as a compiled subgraph.

    Args:
        checkpointer: AsyncPostgresSaver for state persistence

    Returns:
        Compiled StateGraph with HITL support
    """
    executor = DocumentExecutor(checkpointer=checkpointer)
    return executor.build_workflow()
