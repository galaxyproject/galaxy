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

from galaxy.agents.router import RoutingDecision
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
        ai_api_key = os.environ.get("GALAXY_TEST_AI_API_KEY")
        ai_api_base_url = os.environ.get("GALAXY_TEST_AI_API_BASE_URL")
        ai_model = os.environ.get("GALAXY_TEST_AI_MODEL")
        if ai_api_key:
            config["ai_api_key"] = ai_api_key
        if ai_api_base_url:
            config["ai_api_base_url"] = ai_api_base_url
        if ai_model:
            config["ai_model"] = ai_model


def _create_deps_with_mock_model(self, trans, user):
    """Replacement for AgentService.create_dependencies that injects a mock model_factory."""
    from galaxy.agents import (
        agent_registry,
        GalaxyAgentDependencies,
    )

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

    @patch("galaxy.managers.agents.AgentService.create_dependencies", _create_deps_with_mock_model)
    @patch("galaxy.agents.custom_tool.Agent")
    @patch("galaxy.agents.router.Agent")
    def test_query_agent_auto_routing_mocked(self, mock_router_agent_class, mock_custom_tool_agent_class):
        """Test automatic agent routing with mocked LLM."""
        # Set up mock router agent
        mock_router_agent = AsyncMock()
        mock_router_agent_class.return_value = mock_router_agent

        # Mock routing decision - returns RoutingDecision object
        async def mock_router_run(query, *args, **kwargs):
            result = MagicMock()
            if "BWA" in query or "tool" in query.lower():
                result.data = RoutingDecision(
                    primary_agent="custom_tool",
                    reasoning="Tool creation request detected",
                    complexity="simple",
                    confidence="high",
                )
            else:
                result.data = RoutingDecision(
                    primary_agent="orchestrator",
                    reasoning="General query",
                    complexity="simple",
                    confidence="medium",
                )
            return result

        mock_router_agent.run = mock_router_run

        # Set up mock custom_tool agent (created after routing)
        mock_custom_tool_agent = AsyncMock()
        mock_custom_tool_agent_class.return_value = mock_custom_tool_agent

        # Mock tool creation response
        mock_tool = UserToolSource(
            **{
                "class": "GalaxyUserTool",
                "id": "bwa-mem-paired",
                "name": "BWA-MEM Paired End",
                "version": "1.0.0",
                "description": "BWA-MEM for paired-end reads",
                "container": "biocontainers/bwa:latest",
                "shell_command": "bwa mem ref.fa read1.fq read2.fq > output.sam",
                "inputs": [],
                "outputs": [],
            }
        )

        async def mock_custom_tool_run(*args, **kwargs):
            result = MagicMock()
            result.data = mock_tool
            result.output = mock_tool
            return result

        mock_custom_tool_agent.run = mock_custom_tool_run

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
        assert "routing_info" in data
        assert data["routing_info"]["selected_agent"] == "custom_tool"

    @patch("galaxy.managers.agents.AgentService.create_dependencies", _create_deps_with_mock_model)
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
            result.data = mock_tool
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

    @patch("galaxy.managers.agents.AgentService.create_dependencies", _create_deps_with_mock_model)
    @patch("galaxy.agents.error_analysis.Agent")
    def test_query_error_analysis_agent_mocked(self, mock_agent_class):
        """Test the error analysis agent with mocked LLM."""
        mock_agent = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock error analysis
        async def mock_run(*args, **kwargs):
            from galaxy.agents.error_analysis import ErrorAnalysisResult

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
            result.data = mock_analysis
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
