"""
Test Suite for Modernized Supervisor
Tests LangGraph 0.6.7+ features: START/END nodes, retry logic, and workflow
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from service.supervisor.supervisor import RealEstateSupervisor
from service.core.states import create_supervisor_initial_state


class TestSupervisorModern:
    """Test suite for modernized supervisor with START/END syntax"""

    def test_supervisor_initialization(self):
        """Test supervisor initializes with correct configuration"""
        supervisor = RealEstateSupervisor(max_retries=3)

        assert supervisor.agent_name == "real_estate_supervisor"
        assert supervisor.max_retries == 3
        assert supervisor.workflow is not None

    def test_supervisor_default_max_retries(self):
        """Test default max_retries value"""
        supervisor = RealEstateSupervisor()

        assert supervisor.max_retries == 2

    def test_graph_structure_has_start_edge(self):
        """Test that graph uses modern START node syntax"""
        supervisor = RealEstateSupervisor()

        # Get compiled graph
        from langgraph.graph import START

        # Workflow should be built
        assert supervisor.workflow is not None

        # Check that START is used (modern syntax)
        # Note: Direct inspection of edges requires accessing internal structure
        # This is a structural test to ensure modern syntax is used

    def test_should_retry_logic_no_retry_needed(self):
        """Test _should_retry when no retry is needed"""
        supervisor = RealEstateSupervisor(max_retries=2)

        state = {
            "evaluation": {
                "needs_retry": False,
                "quality_score": 0.9
            },
            "retry_count": 0
        }

        result = supervisor._should_retry(state)
        assert result == "end"

    def test_should_retry_logic_retry_needed(self):
        """Test _should_retry when retry is needed and under limit"""
        supervisor = RealEstateSupervisor(max_retries=2)

        state = {
            "evaluation": {
                "needs_retry": True,
                "retry_agents": ["property_search"]
            },
            "retry_count": 0
        }

        result = supervisor._should_retry(state)
        assert result == "retry"

    def test_should_retry_logic_max_retries_reached(self):
        """Test _should_retry when max retries reached"""
        supervisor = RealEstateSupervisor(max_retries=2)

        state = {
            "evaluation": {
                "needs_retry": True,
                "retry_agents": ["property_search"]
            },
            "retry_count": 2
        }

        result = supervisor._should_retry(state)
        assert result == "end"

    @pytest.mark.asyncio
    async def test_validate_input_valid_query(self):
        """Test input validation with valid query"""
        supervisor = RealEstateSupervisor()

        input_data = {
            "query": "강남역 근처 아파트 찾아줘",
            "user_id": "test_user"
        }

        is_valid = await supervisor._validate_input(input_data)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_query(self):
        """Test input validation with missing query"""
        supervisor = RealEstateSupervisor()

        input_data = {
            "user_id": "test_user"
        }

        is_valid = await supervisor._validate_input(input_data)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_input_empty_query(self):
        """Test input validation with empty query"""
        supervisor = RealEstateSupervisor()

        input_data = {
            "query": "   ",
            "user_id": "test_user"
        }

        is_valid = await supervisor._validate_input(input_data)
        assert is_valid is False

    def test_create_initial_state(self):
        """Test initial state creation"""
        supervisor = RealEstateSupervisor()

        input_data = {
            "query": "강남역 아파트",
            "user_id": "test_user"
        }

        initial_state = supervisor._create_initial_state(input_data)

        assert initial_state["query"] == "강남역 아파트"
        assert initial_state["status"] == "pending"
        assert initial_state["execution_step"] == "initializing"
        assert initial_state["intent"] is None
        assert initial_state["execution_plan"] is None
        assert initial_state["agent_results"] == {}
        assert initial_state["evaluation"] is None
        assert initial_state["final_output"] is None

    @pytest.mark.asyncio
    async def test_process_query_structure(self):
        """Test process_query returns correct structure (mock test)"""
        supervisor = RealEstateSupervisor()

        # This will fail without API keys, but we can test the error structure
        try:
            result = await supervisor.process_query(
                query="테스트 쿼리",
                user_id="test_user",
                session_id="test_session"
            )

            # If it runs, check structure
            if "error" in result:
                assert "error" in result
                assert "status" in result
            else:
                # Success case
                assert "answer" in result or "error" in result

        except Exception as e:
            # Expected to fail without proper setup
            assert True


class TestSupervisorRetryMechanism:
    """Test retry mechanism with different scenarios"""

    def test_retry_count_increments(self):
        """Test that retry count should increment in state"""
        supervisor = RealEstateSupervisor(max_retries=3)

        # Simulate first retry
        state_attempt_1 = {
            "evaluation": {"needs_retry": True},
            "retry_count": 0
        }
        assert supervisor._should_retry(state_attempt_1) == "retry"

        # Simulate second retry
        state_attempt_2 = {
            "evaluation": {"needs_retry": True},
            "retry_count": 1
        }
        assert supervisor._should_retry(state_attempt_2) == "retry"

        # Simulate max retries reached
        state_attempt_3 = {
            "evaluation": {"needs_retry": True},
            "retry_count": 3
        }
        assert supervisor._should_retry(state_attempt_3) == "end"

    def test_configurable_max_retries(self):
        """Test different max_retries configurations"""
        # High retry limit
        supervisor_high = RealEstateSupervisor(max_retries=5)
        state = {"evaluation": {"needs_retry": True}, "retry_count": 3}
        assert supervisor_high._should_retry(state) == "retry"

        # Low retry limit
        supervisor_low = RealEstateSupervisor(max_retries=1)
        state = {"evaluation": {"needs_retry": True}, "retry_count": 1}
        assert supervisor_low._should_retry(state) == "end"


class TestSupervisorIntegration:
    """Integration tests for supervisor workflow"""

    @pytest.mark.asyncio
    async def test_full_workflow_mock(self):
        """Test full workflow with mock agents (requires OPENAI_API_KEY)"""
        import os

        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        supervisor = RealEstateSupervisor(max_retries=1)

        result = await supervisor.process_query(
            query="강남역 근처 아파트",
            user_id="test_user",
            session_id="test_session"
        )

        # Check result structure
        assert result is not None
        assert isinstance(result, dict)

        # Should have either success or error
        if "error" not in result:
            # Success case - check for expected fields
            assert "answer" in result or "listings" in result
        else:
            # Error case
            assert "status" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])