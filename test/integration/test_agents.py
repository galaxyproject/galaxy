"""Test Galaxy AI agents API and functionality.

This module contains two test suites:
1. Mocked tests - Deterministic tests with mocked LLM responses (always run)
2. Live LLM tests - Integration tests requiring configured LLM (optional, marked with @pytest.mark.requires_llm)

## Running the tests:

### API tests (Galaxy test instance auto-configured):
    # Run mocked API tests (Galaxy test framework handles setup):
    pytest test/integration/test_agents.py::TestAgentsApiMocked -v

    # Run live LLM API tests:
    GALAXY_TEST_ENABLE_LIVE_LLM=1 pytest test/integration/test_agents.py::TestAgentsApiLiveLLM -v

### Configuration for live API tests (TestAgentsApiLiveLLM):
    export GALAXY_TEST_AI_API_KEY="your-api-key"
    export GALAXY_TEST_AI_MODEL="llama-4-scout"
    export GALAXY_TEST_AI_API_BASE_URL="http://localhost:4000/v1/"
    export GALAXY_TEST_ENABLE_LIVE_LLM=1

### Configuration for live unit tests (TestAgentUnitLiveLLM):
    export GALAXY_AI_API_KEY="your-api-key"
    export GALAXY_AI_MODEL="llama-4-scout"
    export GALAXY_AI_API_BASE_URL="http://localhost:4000/v1/"
    export GALAXY_TEST_ENABLE_LIVE_LLM=1
"""

import logging
import os
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

from galaxy.agents import (
    agent_registry,
    GalaxyAgentDependencies,
)
from galaxy.agents.error_analysis import ErrorAnalysisResult
from galaxy.tool_util_models import UserToolSource
from galaxy.util.unittest_utils import pytestmark_live_llm
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase

log = logging.getLogger(__name__)


class AgentIntegrationTestCase(IntegrationTestCase):
    """Base class for agent integration tests."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # AI/LLM configuration for agent tests
        if ai_api_key := os.environ.get("GALAXY_TEST_AI_API_KEY"):
            config["ai_api_key"] = ai_api_key
        if ai_api_base_url := os.environ.get("GALAXY_TEST_AI_API_BASE_URL"):
            config["ai_api_base_url"] = ai_api_base_url
        if ai_model := os.environ.get("GALAXY_TEST_AI_MODEL"):
            config["ai_model"] = ai_model


def _create_deps_with_mock_model(self, trans, user):
    """Replacement for AgentService.create_dependencies that injects a mock model_factory."""
    toolbox = trans.app.toolbox if hasattr(trans, "app") and hasattr(trans.app, "toolbox") else None
    return GalaxyAgentDependencies(
        trans=trans,
        user=user,
        config=self.config,
        job_manager=self.job_manager,
        toolbox=toolbox,
        get_agent=agent_registry.get_agent,
        model_factory=lambda: MagicMock(),
    )


class TestAgentsApiMocked(AgentIntegrationTestCase):
    """Test the Galaxy AI agents API with mocked LLM responses.

    These tests use mocked LLM responses for deterministic testing.
    They always run in CI and don't require any LLM configuration.
    """

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_list_agents(self):
        """Test listing available agents (no LLM needed)."""
        response = self._get("ai/agents")
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "agents" in data
        agents = data["agents"]
        assert len(agents) > 0
        # Check that core agents are registered
        agent_types = [a["agent_type"] for a in agents]
        assert "router" in agent_types
        assert "custom_tool" in agent_types
        assert "error_analysis" in agent_types

    @patch(
        "galaxy.managers.agents.AgentService.create_dependencies",
        _create_deps_with_mock_model,
    )
    @patch("galaxy.agents.router.Agent")
    def test_query_agent_auto_routing_mocked(self, mock_router_agent_class):
        """Test automatic agent routing with mocked LLM.

        With the new router architecture, the router uses output functions
        and returns the final response directly (either answering or handing
        off to specialists internally).
        """
        # Set up mock router agent
        mock_router_agent = AsyncMock()
        mock_router_agent_class.return_value = mock_router_agent

        # Mock router response - now returns string directly
        async def mock_router_run(query, *args, **kwargs):
            result = MagicMock()
            if "BWA" in query or "tool" in query.lower():
                # Simulate what custom_tool handoff would return
                result.output = "I've created a BWA-MEM tool for paired-end reads. The tool definition includes inputs for reference and read files."
            else:
                # Direct response from router
                result.output = "I'm Galaxy's AI assistant. How can I help you today?"
            return result

        mock_router_agent.run = mock_router_run

        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a BWA-MEM tool for paired-end reads",
                "agent_type": "auto",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        # Router now returns content in the response object
        assert "response" in data
        assert "content" in data["response"]
        assert "BWA" in data["response"]["content"] or len(data["response"]["content"]) > 0

    @patch(
        "galaxy.managers.agents.AgentService.create_dependencies",
        _create_deps_with_mock_model,
    )
    @patch("galaxy.agents.custom_tool.Agent")
    def test_query_custom_tool_agent_mocked(self, mock_agent_class):
        """Test the custom tool agent with mocked LLM."""
        mock_agent = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock tool creation with UserToolSource
        mock_tool = UserToolSource(
            **{
                "class": "GalaxyUserTool",
                "id": "line-counter",
                "name": "Line Counter",
                "version": "1.0.0",
                "description": "Counts lines in a file",
                "container": "ubuntu:latest",
                "shell_command": "wc -l < $(inputs.input_file.path) > output.txt",
                "inputs": [],
                "outputs": [],
            }
        )

        async def mock_run(*args, **kwargs):
            result = MagicMock()
            result.output = mock_tool
            return result

        mock_agent.run = mock_run

        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a simple tool that counts lines in a file",
                "agent_type": "custom_tool",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        # Response structure is {'response': {..., 'metadata': {...}}, 'routing_info': ..., ...}
        assert "response" in data
        assert "metadata" in data["response"]
        assert data["response"]["metadata"]["tool_id"] == "line-counter"
        assert "wc -l" in data["response"]["metadata"]["tool_yaml"]

        # Verify suggestions are present and valid
        suggestions = data["response"].get("suggestions", [])
        assert len(suggestions) >= 1, "Custom tool should return at least one suggestion"
        # Should have a SAVE_TOOL suggestion with required parameters
        save_suggestions = [s for s in suggestions if s["action_type"] == "save_tool"]
        assert len(save_suggestions) == 1, "Should have exactly one SAVE_TOOL suggestion"
        assert save_suggestions[0]["parameters"].get("tool_yaml"), "SAVE_TOOL must have tool_yaml"
        assert save_suggestions[0]["parameters"].get("tool_id"), "SAVE_TOOL must have tool_id"

    @patch(
        "galaxy.managers.agents.AgentService.create_dependencies",
        _create_deps_with_mock_model,
    )
    @patch("galaxy.agents.error_analysis.Agent")
    def test_query_error_analysis_agent_mocked(self, mock_agent_class):
        """Test the error analysis agent with mocked LLM."""
        mock_agent = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock error analysis
        async def mock_run(*args, **kwargs):
            result = MagicMock()
            mock_analysis = ErrorAnalysisResult(
                error_category="tool_configuration",
                error_severity="medium",
                likely_cause="The command 'samtools' was not found in PATH",
                solution_steps=[
                    "Install samtools using conda",
                    "Check tool dependencies",
                    "Verify container configuration",
                ],
                confidence="high",
            )
            result.output = mock_analysis
            return result

        mock_agent.run = mock_run

        # Don't pass a job_id - the agent handles missing job context gracefully
        # and we're testing the mocked LLM response, not job lookup
        response = self._post(
            "ai/agents/query",
            data={
                "query": "Why did my job fail? stderr shows: command not found: samtools",
                "agent_type": "error_analysis",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        # Response structure is {'response': {..., 'content': ...}, ...}
        assert "response" in data
        assert "content" in data["response"]
        # Should mention the error type or solution
        content = data["response"]["content"].lower()
        assert "command" in content or "samtools" in content or "not found" in content

        # Suggestions are optional - only returned for actionable items like CONTACT_SUPPORT
        # In this mock, requires_admin=False, so no suggestions expected
        suggestions = data["response"].get("suggestions", [])
        for suggestion in suggestions:
            assert "action_type" in suggestion
            assert "description" in suggestion
            assert "confidence" in suggestion


# ============================================================================
# LIVE LLM TEST SUITE - Requires configured LLM
# ============================================================================


@pytestmark_live_llm
class TestAgentsApiLiveLLM(AgentIntegrationTestCase):
    """Test Galaxy AI agents API with real LLM.

    These tests require a configured LLM and will be skipped unless
    GALAXY_TEST_ENABLE_LIVE_LLM=1 is set.
    """

    def test_query_agent_auto_routing_live(self):
        """Test automatic agent routing with live LLM."""
        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a BWA-MEM tool for paired-end reads",
                "agent_type": "auto",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        assert "agent_type" in data["response"]
        # Router should route this to custom_tool
        assert data.get("routing_info", {}).get("selected_agent") == "custom_tool"

    def test_query_custom_tool_agent_live(self):
        """Test custom tool agent with live LLM."""
        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a simple tool that counts lines in a file",
                "agent_type": "custom_tool",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        agent_response = data["response"]
        assert "content" in agent_response
        assert "metadata" in agent_response
        assert "tool_id" in agent_response["metadata"]
        assert "tool_yaml" in agent_response["metadata"]
        # Check that it created something sensible
        tool_yaml = agent_response["metadata"]["tool_yaml"]
        assert "command" in tool_yaml or "shell_command" in tool_yaml

    def test_error_analysis_endpoint_live(self):
        """Test the dedicated error-analysis endpoint."""
        response = self._post(
            "ai/agents/error-analysis",
            data={
                "query": "My BWA job failed with exit code 137 and stderr shows 'Killed'",
                "error_details": {"tool_id": "bwa_mem", "exit_code": 137},
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "content" in data
        assert "confidence" in data
        # Should mention memory or OOM since exit code 137 is SIGKILL
        content = data["content"].lower()
        assert any(word in content for word in ["memory", "kill", "resource", "oom"])

    def test_custom_tool_endpoint_live(self):
        """Test the dedicated custom-tool endpoint."""
        response = self._post(
            "ai/agents/custom-tool",
            data={
                "query": "Create a tool that counts sequences in a FASTA file",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "content" in data
        assert "metadata" in data
        # Should generate tool YAML
        metadata = data["metadata"]
        assert "tool_yaml" in metadata or "tool_id" in metadata

    def test_chat_endpoint_live(self):
        """Test the chat endpoint with auto routing."""
        response = self._post(
            "chat?query=What%20tools%20are%20available%20for%20RNA-seq%3F&agent_type=auto",
            data={},
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        # Should return some content about RNA-seq
        assert len(data["response"]) > 0

    def test_chat_history_endpoint(self):
        """Test the chat history endpoint."""
        response = self._get("chat/history?limit=5")
        self._assert_status_code_is_ok(response)
        data = response.json()
        # Should return a list (may be empty)
        assert isinstance(data, list)


# ============================================================================
# AgentOperationsManager ID Encoding Tests
# ============================================================================


class TestAgentOperationsManagerEncoding(AgentIntegrationTestCase):
    """Test AgentOperationsManager ID encoding.

    These tests verify that the _encode_ids_in_response helper correctly
    encodes Galaxy database IDs so agents can use them in subsequent API calls.
    """

    def test_encode_ids_helper_encodes_nested_ids(self):
        """Test that _encode_ids_in_response correctly encodes nested IDs."""
        from galaxy.managers.agent_operations import AgentOperationsManager
        from galaxy.managers.context import ProvidesUserContext

        # Create a minimal transaction context just for encoding
        class MinimalTrans(ProvidesUserContext):
            def __init__(self, app):
                self._app = app

            @property
            def app(self):
                return self._app

            @property
            def user(self):
                return None

            @property
            def security(self):
                return self._app.security

            @property
            def user_is_admin(self):
                return False

        trans = MinimalTrans(self._app)
        ops = AgentOperationsManager(app=self._app, trans=trans)

        # Test data with nested structure containing integer IDs
        test_data = {
            "id": 123,
            "name": "test",
            "nested": {"id": 456, "history_id": 789},
            "list_items": [{"id": 111, "dataset_id": 222}, {"id": 333}],
        }

        result = ops._encode_ids_in_response(test_data)

        # Top-level id should be encoded
        assert isinstance(result["id"], str)
        assert len(result["id"]) >= 16

        # Non-ID field should be unchanged
        assert result["name"] == "test"

        # Nested IDs should be encoded
        assert isinstance(result["nested"]["id"], str)
        assert isinstance(result["nested"]["history_id"], str)

        # List items should have encoded IDs
        assert isinstance(result["list_items"][0]["id"], str)
        assert isinstance(result["list_items"][0]["dataset_id"], str)
        assert isinstance(result["list_items"][1]["id"], str)

    def test_encode_ids_preserves_non_id_fields(self):
        """Test that encoding preserves non-ID fields unchanged."""
        from galaxy.managers.agent_operations import AgentOperationsManager
        from galaxy.managers.context import ProvidesUserContext

        class MinimalTrans(ProvidesUserContext):
            def __init__(self, app):
                self._app = app

            @property
            def app(self):
                return self._app

            @property
            def user(self):
                return None

            @property
            def security(self):
                return self._app.security

            @property
            def user_is_admin(self):
                return False

        trans = MinimalTrans(self._app)
        ops = AgentOperationsManager(app=self._app, trans=trans)

        test_data = {
            "id": 1,
            "name": "My History",
            "annotation": "Test annotation",
            "count": 42,
            "empty_list": [],
            "tags": ["tag1", "tag2"],
        }

        result = ops._encode_ids_in_response(test_data)

        # id should be encoded
        assert isinstance(result["id"], str)

        # Other fields should be preserved exactly
        assert result["name"] == "My History"
        assert result["annotation"] == "Test annotation"
        assert result["count"] == 42
        assert result["empty_list"] == []
        assert result["tags"] == ["tag1", "tag2"]

    def test_encode_ids_handles_already_encoded_ids(self):
        """Test that string IDs (already encoded) are left unchanged."""
        from galaxy.managers.agent_operations import AgentOperationsManager
        from galaxy.managers.context import ProvidesUserContext

        class MinimalTrans(ProvidesUserContext):
            def __init__(self, app):
                self._app = app

            @property
            def app(self):
                return self._app

            @property
            def user(self):
                return None

            @property
            def security(self):
                return self._app.security

            @property
            def user_is_admin(self):
                return False

        trans = MinimalTrans(self._app)
        ops = AgentOperationsManager(app=self._app, trans=trans)

        # If IDs are already strings, they should be left unchanged
        test_data = {
            "id": "abc123def456",
            "history_id": "already_encoded_id",
        }

        result = ops._encode_ids_in_response(test_data)

        # String IDs should remain unchanged
        assert result["id"] == "abc123def456"
        assert result["history_id"] == "already_encoded_id"
