"""Unit tests for Galaxy agent implementations.

There are three classes here - they break into tests that require a live LLM
and those that do not.

1. Mocked tests - Deterministic tests with mocked LLM responses (always run) - TestAgentUnitMocked
2. Live LLM tests - "Integration" tests requiring configured LLM (optional, marked with @pytest.mark.requires_llm)
   TestAgentUnitLiveLLM, TestAgentConsistencyLiveLLM

### Configuration for live API tests (TestAgentsApiLiveLLM):
    export GALAXY_TEST_AI_API_KEY="your-api-key"
    export GALAXY_TEST_AI_MODEL="llama-4-scout"
    export GALAXY_TEST_AI_API_BASE_URL="http://localhost:4000/v1/"
    export GALAXY_TEST_ENABLE_LIVE_LLM=1
"""

import os
from typing import (
    Any,
)
from unittest import mock
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

# Skip entire module if pydantic_ai is not installed
pydantic_ai = pytest.importorskip("pydantic_ai")
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from galaxy.agents import (
    agent_registry,
    CustomToolAgent,
    ErrorAnalysisAgent,
    GalaxyAgentDependencies,
    QueryRouterAgent,
)
from galaxy.agents.error_analysis import ErrorAnalysisResult
from galaxy.agents.orchestrator import (
    AgentPlan,
    WorkflowOrchestratorAgent,
)
from galaxy.schema.agents import ConfidenceLevel
from galaxy.tool_util_models import UserToolSource
from galaxy.util.unittest_utils import pytestmark_live_llm


class TestAgentUnitMocked:
    """Unit tests for agent implementations."""

    def setup_method(self):
        """Set up mock dependencies for each test."""
        self.mock_config = mock.Mock()
        self.mock_config.ai_api_key = "test-key"
        self.mock_config.ai_model = "llama-4-scout"
        self.mock_config.ai_api_base_url = "http://localhost:4000/v1/"

        self.mock_user = mock.Mock()
        self.mock_user.id = 1
        self.mock_user.username = "test_user"

        self.mock_trans = mock.Mock()
        self.mock_trans.app.config = self.mock_config
        self.mock_trans.user = self.mock_user

        self.deps = GalaxyAgentDependencies(
            trans=self.mock_trans,
            user=self.mock_user,
            config=self.mock_config,
            job_manager=None,
        )

    def test_agent_config_fallback_chain(self):
        """Test per-agent configuration with fallback logic."""
        # Set up mock config with inference_services
        self.mock_config.inference_services = {
            "default": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            "custom_tool": {
                "model": "claude-sonnet-4-5",
                "temperature": 0.3,
                "max_tokens": 3000,
            },
        }

        # Test agent with specific config
        custom_tool_agent = CustomToolAgent(self.deps)
        assert custom_tool_agent._get_agent_config("model") == "claude-sonnet-4-5"
        assert custom_tool_agent._get_agent_config("temperature") == 0.3
        assert custom_tool_agent._get_agent_config("max_tokens") == 3000

        # Test agent that falls back to default
        error_agent = ErrorAnalysisAgent(self.deps)
        assert error_agent._get_agent_config("model") == "gpt-4o-mini"
        assert error_agent._get_agent_config("temperature") == 0.7
        assert error_agent._get_agent_config("max_tokens") == 2000

        # Test fallback to global config when inference_services not set
        self.mock_config.inference_services = None
        router_agent = QueryRouterAgent(self.deps)
        assert router_agent._get_agent_config("model") == "llama-4-scout"  # From ai_model
        assert router_agent._get_agent_config("api_key") == "test-key"  # From ai_api_key

        # Test custom default value
        assert router_agent._get_agent_config("temperature", 0.5) == 0.5
        assert router_agent._get_agent_config("max_tokens", 1500) == 1500

    @pytest.mark.asyncio
    async def test_custom_tool_agent_structured_output(self):
        """Test custom tool agent with structured output support."""
        # Test with a model that supports structured output (gpt-4o)
        self.mock_config.ai_model = "gpt-4o"
        agent = CustomToolAgent(self.deps)

        # Mock the agent run to return a UserToolSource
        with mock.patch.object(agent.agent, "run") as mock_run:
            mock_tool = UserToolSource(
                **{
                    "class": "GalaxyUserTool",
                    "id": "test-tool",
                    "name": "Test Tool",
                    "version": "1.0.0",
                    "description": "A test tool",
                    "container": "ubuntu:latest",
                    "shell_command": "echo test",
                    "inputs": [],
                    "outputs": [],
                }
            )

            mock_result = mock.Mock()
            mock_result.output = mock_tool
            mock_run.return_value = mock_result

            response = await agent.process("Create a test tool")

            assert response.confidence.value in ["high", "medium"]
            assert response.metadata["tool_id"] == "test-tool"
            assert response.metadata["method"] == "structured"

    @pytest.mark.asyncio
    async def test_custom_tool_agent_requires_structured_output(self):
        """Test custom tool agent returns helpful error when model doesn't support structured output."""
        # Test with DeepSeek which doesn't support structured output
        self.mock_config.ai_model = "deepseek-r1"
        agent = CustomToolAgent(self.deps)

        response = await agent.process("Create a BWA-MEM tool")

        # Should return capability error, not attempt fallback
        assert response.metadata.get("error") == "model_capability"
        assert response.metadata.get("requires") == "structured_output"
        assert "structured output" in response.content.lower()
        assert response.confidence.value == "low"

    def test_agent_registry(self):
        """Test that all required agents are registered."""
        required_agents = [
            "router",
            "custom_tool",
            "error_analysis",
        ]

        for agent_type in required_agents:
            assert agent_registry.is_registered(agent_type), f"Agent {agent_type} should be registered"
            # Verify we can get agent info
            info = agent_registry.get_agent_info(agent_type)
            assert info["agent_type"] == agent_type
            assert "class_name" in info

    def test_error_analysis_no_suggestions_without_admin(self):
        """Verify _create_suggestions only returns actionable suggestions.

        Solution steps and alternatives are guidance, not executable actions,
        so they shouldn't generate suggestions.
        """
        analysis = ErrorAnalysisResult(
            error_category="tool_configuration",
            error_severity="medium",
            likely_cause="Missing input file",
            solution_steps=["Check input", "Re-upload file"],
            confidence="high",
            requires_admin=False,
        )

        agent = ErrorAnalysisAgent(self.deps)
        suggestions = agent._create_suggestions(analysis)

        # No actionable suggestions when admin not required
        assert suggestions == []

    def test_error_analysis_suggestions_with_admin_required(self):
        """When requires_admin=True, should suggest contacting support."""
        analysis = ErrorAnalysisResult(
            error_category="system_error",
            error_severity="high",
            likely_cause="Disk quota exceeded",
            solution_steps=["Contact admin"],
            confidence="high",
            requires_admin=True,
        )

        agent = ErrorAnalysisAgent(self.deps)
        suggestions = agent._create_suggestions(analysis)

        assert len(suggestions) == 1
        assert suggestions[0].action_type.value == "contact_support"
        assert suggestions[0].confidence == ConfidenceLevel.HIGH

    @pytest.mark.skip(reason="TestModel API changed in pydantic-ai, needs update for new version")
    @pytest.mark.asyncio
    async def test_router_with_test_model(self):
        """Test router using pydantic-ai TestModel for deterministic output."""
        # TODO: Update this test for newer pydantic-ai TestModel API
        # The router now uses output functions and returns AgentResponse directly
        # rather than RoutingDecision objects
        with patch("galaxy.agents.router.QueryRouterAgent._create_agent") as mock_create:
            # Create TestModel with predictable output
            test_model = TestModel()
            # This API no longer exists in newer pydantic-ai versions
            # test_model.set_result({...})

            test_agent: Any = Agent(  # type: ignore[call-overload]
                "test-router",
                model=test_model,
                output_type=str,
            )
            mock_create.return_value = test_agent

            router = QueryRouterAgent(self.deps)
            response = await router.process("Create a BWA tool")

            # Router now returns AgentResponse with content
            assert response.content is not None
            assert response.agent_type == "router"

    @pytest.mark.asyncio
    async def test_router_extracts_output_attribute(self):
        """Test that router correctly extracts .output from pydantic-ai results.

        pydantic-ai's AgentRunResult has .output, not .data. This test ensures
        the router extracts the actual response content, not the object repr.
        """
        router = QueryRouterAgent(self.deps)

        with mock.patch.object(router, "_run_with_retry") as mock_run:
            # Mock result with only .output (like real pydantic-ai AgentRunResult)
            mock_result = mock.Mock(spec=["output"])
            mock_result.output = "Hello! I'm Galaxy's AI assistant. How can I help you today?"
            mock_run.return_value = mock_result

            response = await router.process("Hi")

            # Should extract the actual content, not show object repr
            assert response.content == "Hello! I'm Galaxy's AI assistant. How can I help you today?"
            assert "Mock" not in response.content
            assert "AgentRunResult" not in response.content

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_agent_mocked(self):
        """Test WorkflowOrchestratorAgent with mocked responses."""
        agent = WorkflowOrchestratorAgent(self.deps)

        # Test 1: Query that should NOT trigger orchestration (single agent)
        with patch.object(agent, "_get_agent_plan") as mock_get_plan:
            # Mock a plan that indicates single agent is sufficient
            mock_get_plan.return_value = AgentPlan(
                agents=["error_analysis"],
                sequential=False,
                reasoning="Single error analysis needed",
            )

            # Mock the actual agent call to avoid running it
            with patch("galaxy.agents.agent_registry.get_agent") as mock_get_agent:
                mock_error_agent = AsyncMock()
                mock_error_agent.process.return_value = MagicMock(
                    content="The job failed due to memory limits.",
                    agent_type="error_analysis",
                )
                mock_get_agent.return_value = mock_error_agent

                response = await agent.process("Why did my job fail?")

                # Should not orchestrate, just return single agent response
                assert response.agent_type == "orchestrator"
                assert response.metadata.get("agents_used") == ["error_analysis"]
                assert "memory limits" in response.content

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_sequential_execution(self):
        """Test orchestrator sequential workflow execution."""
        agent = WorkflowOrchestratorAgent(self.deps)

        # Mock a complex plan requiring sequential orchestration
        complex_plan = AgentPlan(
            agents=["error_analysis", "custom_tool"],
            sequential=True,
            reasoning="Multi-step workflow: error diagnosis -> tool creation",
        )

        # Mock each agent call in the sequential workflow
        with (
            patch.object(agent, "_get_agent_plan") as mock_get_plan,
            patch("galaxy.agents.agent_registry.get_agent") as mock_get_agent,
        ):
            mock_get_plan.return_value = complex_plan

            # Mock individual agent responses
            mock_error_agent = AsyncMock()
            mock_error_agent.process.return_value = MagicMock(
                content="Tool failed due to memory issues", agent_type="error_analysis"
            )

            mock_custom_tool_agent = AsyncMock()
            mock_custom_tool_agent.process.return_value = MagicMock(
                content="Created custom tool wrapper", agent_type="custom_tool"
            )

            # Configure mock to return different agents
            def get_agent_side_effect(agent_type, deps):
                if agent_type == "error_analysis":
                    return mock_error_agent
                elif agent_type == "custom_tool":
                    return mock_custom_tool_agent
                else:
                    raise ValueError(f"Unexpected agent type: {agent_type}")

            mock_get_agent.side_effect = get_agent_side_effect

            response = await agent.process("My tool failed with memory error, help me create a fixed version")

            # Verify orchestration occurred
            assert response.agent_type == "orchestrator"
            assert response.metadata.get("execution_type") == "sequential"
            assert "memory issues" in response.content
            assert "custom tool" in response.content.lower()

            # Verify agents were called in sequence
            assert mock_error_agent.process.called
            assert mock_custom_tool_agent.process.called

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_parallel_execution(self):
        """Test orchestrator parallel workflow execution."""
        agent = WorkflowOrchestratorAgent(self.deps)

        # Mock parallel plan
        parallel_plan = AgentPlan(
            agents=["error_analysis", "custom_tool"],
            sequential=False,
            reasoning="Independent tasks can run in parallel",
        )

        with (
            patch.object(agent, "_get_agent_plan") as mock_get_plan,
            patch("galaxy.agents.agent_registry.get_agent") as mock_get_agent,
        ):
            mock_get_plan.return_value = parallel_plan

            # Mock agent responses
            mock_error_agent = AsyncMock()
            mock_error_agent.process.return_value = MagicMock(
                content="Error diagnosis: memory limit exceeded", agent_type="error_analysis"
            )

            mock_custom_tool_agent = AsyncMock()
            mock_custom_tool_agent.process.return_value = MagicMock(
                content="Custom tool created successfully", agent_type="custom_tool"
            )

            def get_agent_side_effect(agent_type, deps):
                if agent_type == "error_analysis":
                    return mock_error_agent
                elif agent_type == "custom_tool":
                    return mock_custom_tool_agent
                else:
                    raise ValueError(f"Unexpected agent type: {agent_type}")

            mock_get_agent.side_effect = get_agent_side_effect

            response = await agent.process("Help with my error and create a custom tool")

            # Verify parallel execution
            assert response.agent_type == "orchestrator"
            assert response.metadata.get("execution_type") == "parallel"
            assert "Error diagnosis" in response.content
            assert "Custom tool" in response.content

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_generic_fallback_behavior(self):
        """Test orchestrator fallback when planning fails."""
        agent = self._orchestrator_agent()

        # Mock planning failure
        with patch.object(agent, "_get_agent_plan") as mock_get_plan:
            # target handles OSError and ValueError specifically
            mock_get_plan.side_effect = Exception("LLM service unavailable")

            response = await agent.process("Complex query that should trigger fallback")

            # Should fall back gracefully
            assert response.agent_type == "orchestrator"
            assert "having trouble" in response.content

    def _orchestrator_agent(self):
        """Helper to create a patched orchestrator agent with mocked dependencies."""
        agent = WorkflowOrchestratorAgent(self.deps)
        return agent


@pytestmark_live_llm
class TestAgentUnitLiveLLM:
    """Unit tests with real LLM connections."""

    def setup_method(self):
        """Set up real dependencies for live LLM testing."""
        self.mock_config = mock.Mock()
        self.mock_config.ai_api_key = os.environ.get("GALAXY_TEST_AI_API_KEY", "test-key")
        self.mock_config.ai_model = os.environ.get("GALAXY_TEST_AI_MODEL", "llama-4-scout")
        self.mock_config.ai_api_base_url = os.environ.get("GALAXY_TEST_AI_API_BASE_URL", "http://localhost:4000/v1/")

        self.mock_user = mock.Mock()
        self.mock_user.id = 1
        self.mock_user.username = "test_user"

        self.mock_trans = mock.Mock()
        self.mock_trans.app.config = self.mock_config
        self.mock_trans.user = self.mock_user

        self.deps = GalaxyAgentDependencies(
            trans=self.mock_trans,
            user=self.mock_user,
            config=self.mock_config,
            job_manager=None,
        )

    @pytest.mark.asyncio
    async def test_router_agent_responses_live(self):
        """Test router with real LLM - verify it returns appropriate responses."""
        router = QueryRouterAgent(self.deps)

        # Test general question - should get a helpful response
        response = await router.process("How do I run BWA in Galaxy?")
        assert response.content is not None
        assert len(response.content) > 50  # Should have substantial content
        assert response.agent_type == "router"

        # Test tool creation - should trigger custom_tool handoff
        response = await router.process("Create a simple echo tool for Galaxy")
        assert response.content is not None
        assert response.agent_type == "router"

        # Test error query - should trigger error_analysis handoff
        response = await router.process("Why did my job fail with exit code 127?")
        assert response.content is not None
        assert response.agent_type == "router"

    @pytest.mark.asyncio
    async def test_custom_tool_agent_with_scout(self):
        """Test custom tool agent with Scout model."""
        self.mock_config.ai_model = "llama-4-scout"
        agent = CustomToolAgent(self.deps)

        response = await agent.process("Create a simple echo tool")

        assert response.confidence in ["high", "medium"]
        assert "tool_id" in response.metadata
        assert "tool_yaml" in response.metadata
        assert response.metadata["method"] == "structured"

    @pytest.mark.asyncio
    async def test_custom_tool_agent_with_deepseek(self):
        """Test custom tool agent with DeepSeek model."""
        self.mock_config.ai_model = "deepseek-r1"
        agent = CustomToolAgent(self.deps)

        response = await agent.process("Create a simple echo tool")

        # DeepSeek should use fallback
        assert response.metadata["method"] == "simple_template"
        assert "tool_id" in response.metadata
        assert "tool_yaml" in response.metadata


@pytestmark_live_llm
class TestAgentConsistencyLiveLLM:
    """Test agents with a consistent set of questions.

    With the new router architecture using output functions, the router
    handles queries directly or hands off to specialists. We test that
    responses are appropriate for each query type.
    """

    TEST_QUERIES = [
        # Tool creation queries - should trigger custom_tool handoff
        ("Create a simple line counting tool", "tool_creation"),
        ("Build a Galaxy tool that runs samtools sort", "tool_creation"),
        ("I need a wrapper for BWA-MEM", "tool_creation"),
        # Error analysis queries - should trigger error_analysis handoff
        ("Why did my job fail with exit code 127?", "error_analysis"),
        ("Help me debug this memory error", "error_analysis"),
        ("What does 'command not found' mean?", "error_analysis"),
        # General queries - should get direct response from router
        ("Hello", "direct"),
        ("Thank you", "direct"),
        ("What can you do?", "direct"),
        ("How do I run BWA in Galaxy?", "direct"),
    ]

    @pytest.fixture
    def live_deps(self):
        """Create dependencies for live LLM testing."""
        mock_config = mock.Mock()
        mock_config.ai_api_key = os.environ.get("GALAXY_AI_API_KEY", "test-key")
        mock_config.ai_model = os.environ.get("GALAXY_AI_MODEL", "llama-4-scout")
        mock_config.ai_api_base_url = os.environ.get("GALAXY_AI_API_BASE_URL", "http://localhost:4000/v1/")

        mock_user = mock.Mock()
        mock_user.id = 1
        mock_user.username = "test_user"

        mock_trans = mock.Mock()
        mock_trans.app.config = mock_config
        mock_trans.user = mock_user

        return GalaxyAgentDependencies(
            trans=mock_trans,
            user=mock_user,
            config=mock_config,
            job_manager=None,
        )

    @pytest.mark.asyncio
    async def test_response_consistency_live(self, live_deps):
        """Test that responses are appropriate for known query types with live LLM."""
        router = QueryRouterAgent(live_deps)

        for query, _query_type in self.TEST_QUERIES:
            response = await router.process(query)

            # All queries should return a response
            assert response.content is not None, f"Query '{query}' should return content"
            assert len(response.content) > 0, f"Query '{query}' should have non-empty content"
            assert response.agent_type == "router"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,query_type", TEST_QUERIES)
    async def test_individual_query_response_live(self, live_deps, query, query_type):
        """Test each query individually with live LLM."""
        router = QueryRouterAgent(live_deps)
        response = await router.process(query)

        # Verify we get a substantive response
        assert response.content is not None
        assert len(response.content) > 0
        assert response.agent_type == "router"
