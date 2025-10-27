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
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.service_agent.foundation.separated_states import MainSupervisorState

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
        logger.info("📄 DocumentExecutor initialized")

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
        Planning Node: Analyze user query and create document generation plan.

        Current Implementation: Mock/TODO
        - Extracts simple keywords from query
        - Returns generic document structure

        Future Implementation:
        - Use LLM to analyze query intent
        - Determine specific document type (lease contract, legal notice, etc.)
        - Identify required information and sections
        - Plan validation and compliance requirements

        Args:
            state: MainSupervisorState containing user query

        Returns:
            Updated state with planning_result
        """
        logger.info("📋 Planning node: Analyzing document requirements")

        # 🆕 Step Progress: Step 1 (계획 수립) - Start
        await self._update_step_progress(state, step_index=0, status="in_progress", progress=0)

        query = state.get("query", "")

        # TODO: Replace with LLM-based analysis
        planning_result = {
            "document_type": "general",
            "sections": ["introduction", "main_content", "conclusion"],
            "estimated_length": "medium",
            "requires_search": True,
            "search_keywords": self._extract_keywords(query),
            "timestamp": "2025-10-26T00:00:00"
        }

        logger.info(
            f"Planning complete: {planning_result['document_type']} document "
            f"with {len(planning_result['sections'])} sections"
        )

        # 🆕 Step Progress: Step 1 (계획 수립) - Complete
        await self._update_step_progress(state, step_index=0, status="completed", progress=100)

        return {
            "planning_result": planning_result,
            "workflow_status": "running"
        }

    async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Aggregate Node: Consolidate information and request HITL approval.

        This is the CRITICAL HITL node using LangGraph 0.6 interrupt() pattern.

        Workflow:
        1. Perform mock search based on planning keywords
        2. Aggregate search results into coherent content
        3. Call interrupt() to pause execution and request user approval
        4. Resume when parent graph calls Command(resume=user_feedback)
        5. Apply user modifications if action == "modify"

        HITL Pattern (LangGraph 0.6):
        - Uses interrupt() function (NOT NodeInterrupt exception)
        - interrupt() stores value in checkpoint and waits
        - Parent graph retrieves via get_state().tasks[0].interrupts[0]
        - Resume with Command(resume=value)

        Args:
            state: MainSupervisorState containing planning_result

        Returns:
            Updated state with aggregated_content and collaboration_result
        """
        logger.info("📊 Aggregate node: Consolidating search results")

        # 🆕 Step Progress: Step 2 (정보 검증) - Start
        await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)

        planning_result = state.get("planning_result", {})
        keywords = planning_result.get("search_keywords", [])

        # Perform mock search
        # TODO: Replace with actual search tools (legal DB, real estate DB, etc.)
        search_results = self._mock_search(keywords)

        # Aggregate results into coherent content
        aggregated_content = self._aggregate_results(search_results)

        logger.info(f"Aggregation complete: {len(aggregated_content)} characters")

        # 🆕 Step Progress: Step 2 (정보 검증) - Complete
        await self._update_step_progress(state, step_index=1, status="completed", progress=100)

        # 🆕 Step Progress: Step 3 (정보 입력 HITL) - Start
        await self._update_step_progress(state, step_index=2, status="in_progress", progress=0)

        logger.info("⏸️  Requesting human approval via interrupt()")

        # Prepare interrupt value with user-facing data and metadata
        interrupt_value = {
            # User-facing data
            "aggregated_content": aggregated_content,
            "search_results_count": len(search_results),
            "message": "Please review the aggregated content before final document generation.",
            "options": {
                "approve": "Continue with document generation",
                "modify": "Provide feedback for modification",
                "reject": "Cancel document generation"
            },
            # Metadata for parent graph
            "_metadata": {
                "interrupted_by": "aggregate",
                "interrupt_type": "approval",
                "node_name": "document_team.aggregate"
            }
        }

        # Update state before interrupt
        state["aggregated_content"] = aggregated_content
        state["workflow_status"] = "interrupted"

        # ✅ LangGraph 0.6 HITL Pattern: Use interrupt() function
        # Execution pauses here until Command(resume=...) is called
        user_feedback = interrupt(interrupt_value)

        # 🔄 Execution resumes here after Command(resume=user_feedback)
        logger.info("▶️  Workflow resumed with user feedback")
        logger.info(f"User feedback: {user_feedback}")

        # 🆕 Step Progress: Step 3 (정보 입력 HITL) - Complete
        await self._update_step_progress(state, step_index=2, status="completed", progress=100)

        # 🆕 Step Progress: Step 4 (법률 검토) - Start
        await self._update_step_progress(state, step_index=3, status="in_progress", progress=0)

        # Process user feedback
        if user_feedback and user_feedback.get("action") == "modify":
            logger.info("Applying user modifications")
            aggregated_content = self._apply_user_feedback(aggregated_content, user_feedback)

        # 🆕 Step Progress: Step 4 (법률 검토) - Complete
        await self._update_step_progress(state, step_index=3, status="completed", progress=100)

        return {
            "aggregated_content": aggregated_content,
            "collaboration_result": user_feedback,
            "workflow_status": "running",
            "interrupted_by": "aggregate",
            "interrupt_type": "approval"
        }

    async def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Generate Node: Create final document from approved content.

        Current Implementation: Mock/TODO
        - Simple text formatting
        - Builds final_response for client
        - Adds team_results for parent graph

        Future Implementation:
        - Use LLM to create well-formatted document
        - Apply document templates (DOCX, PDF)
        - Use LeaseContractGeneratorTool for lease contracts
        - Run validation and compliance checks

        Args:
            state: MainSupervisorState containing aggregated_content

        Returns:
            Updated state with final_document, final_response, team_results
        """
        logger.info("📝 Generate node: Creating final document")

        # 🆕 Step Progress: Step 5 (문서 생성) - Start
        await self._update_step_progress(state, step_index=4, status="in_progress", progress=0)

        aggregated_content = state.get("aggregated_content", "")
        planning_result = state.get("planning_result", {})
        collaboration_result = state.get("collaboration_result", {})

        # Generate final document
        # TODO: Use LLM and templates for professional formatting
        final_document = self._format_document(
            content=aggregated_content,
            planning=planning_result,
            feedback=collaboration_result
        )

        logger.info(f"Document generation complete: {len(final_document)} characters")

        # 🆕 Step Progress: Step 5 (문서 생성) - Complete
        await self._update_step_progress(state, step_index=4, status="completed", progress=100)

        # 🆕 Step Progress: Step 6 (최종 검토 HITL) - Start (Mock - no actual HITL in current impl)
        await self._update_step_progress(state, step_index=5, status="in_progress", progress=0)

        # Build final_response for client
        doc_type = planning_result.get("document_type", "general")
        user_action = collaboration_result.get("action", "unknown") if collaboration_result else "unknown"

        final_response = {
            "answer": final_document,
            "document_type": doc_type,
            "user_approved": user_action == "approve",
            "user_action": user_action,
            "modifications_applied": user_action == "modify",
            "type": "document"
        }

        logger.info(f"✅ Final response created: type={doc_type}, action={user_action}")

        # Add to team_results for Parent Graph aggregation
        team_results = {
            "document": {
                "status": "success",
                "data": final_response
            }
        }

        logger.info("✅ Document Team results added to team_results")

        # 🆕 Step Progress: Step 6 (최종 검토) - Complete (auto-approved for now)
        await self._update_step_progress(state, step_index=5, status="completed", progress=100)

        return {
            "final_document": final_document,
            "final_response": final_response,
            "workflow_status": "completed",
            "team_results": team_results
        }

    # ==================== Private Helper Methods ====================

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
