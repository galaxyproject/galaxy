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
    Dict,
)
from unittest import mock
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from pydantic_ai.models.test import TestModel

from galaxy.agents import (
    agent_registry,
    CustomToolAgent,
    ErrorAnalysisAgent,
    GalaxyAgentDependencies,
    QueryRouterAgent,
)
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
            mock_result.data = mock_tool
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
            "tool_recommendation",
            "gtn_training",
        ]

        for agent_type in required_agents:
            assert agent_registry.is_registered(agent_type), f"Agent {agent_type} should be registered"
            # Verify we can get agent info
            info = agent_registry.get_agent_info(agent_type)
            assert info["agent_type"] == agent_type
            assert "class_name" in info

    def test_gtn_database_connectivity(self):
        """Test that GTN database is accessible."""
        from galaxy.agents.gtn import GTNSearchDB

        try:
            db = GTNSearchDB()
            metadata = db.get_metadata()
            assert metadata is not None
            assert "version" in metadata or "tutorial_count" in metadata

            # Test basic search
            results = db.search("RNA-seq", limit=1)
            assert isinstance(results, list)
        except Exception as e:
            # GTN database might not be available in test environment
            pytest.skip(f"GTN database not available: {e}")

    @pytest.mark.skip(reason="TestModel API changed in pydantic-ai, needs update for new version")
    @pytest.mark.asyncio
    async def test_router_with_test_model(self):
        """Test router using pydantic-ai TestModel for deterministic output."""
        # TODO: Update this test for newer pydantic-ai TestModel API
        # The TestModel API changed and no longer has set_result()
        with patch("galaxy.agents.router.QueryRouterAgent._create_agent") as mock_create:
            from pydantic_ai import Agent

            # Create TestModel with predictable output
            test_model = TestModel()
            # This API no longer exists in newer pydantic-ai versions
            # test_model.set_result({...})

            test_agent = Agent(
                "test-router",
                model=test_model,
                result_type=Dict[str, Any],
            )
            mock_create.return_value = test_agent

            router = QueryRouterAgent(self.deps)
            decision = await router.route_query("Create a BWA tool")

            assert decision.primary_agent == "custom_tool"
            # confidence is a Literal["low", "medium", "high"], just verify it's set
            assert decision.confidence is not None

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_agent_mocked(self):
        """Test WorkflowOrchestratorAgent with mocked responses."""
        from galaxy.agents.orchestrator import (
            AgentPlan,
            WorkflowOrchestratorAgent,
        )

        agent = WorkflowOrchestratorAgent(self.deps)

        # Test 1: Query that should NOT trigger orchestration (single agent)
        with patch.object(agent, "_get_agent_plan") as mock_get_plan:
            # Mock a plan that indicates single agent is sufficient
            mock_get_plan.return_value = AgentPlan(
                agents=["tool_recommendation"],
                sequential=False,
                reasoning="Single tool recommendation needed",
            )

            # Mock the actual agent call to avoid running it
            with patch("galaxy.agents.agent_registry.get_agent") as mock_get_agent:
                mock_tool_agent = AsyncMock()
                mock_tool_agent.process.return_value = MagicMock(
                    content="Use BWA-MEM for alignment.",
                    agent_type="tool_recommendation",
                )
                mock_get_agent.return_value = mock_tool_agent

                response = await agent.process("I need tools for RNA-seq analysis")

                # Should not orchestrate, just return single agent response
                assert response.agent_type == "orchestrator"
                assert response.metadata.get("agents_used") == ["tool_recommendation"]
                assert "BWA-MEM" in response.content

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_sequential_execution(self):
        """Test orchestrator sequential workflow execution."""
        from galaxy.agents.orchestrator import (
            AgentPlan,
            WorkflowOrchestratorAgent,
        )

        agent = WorkflowOrchestratorAgent(self.deps)

        # Mock a complex plan requiring sequential orchestration
        complex_plan = AgentPlan(
            agents=["error_analysis", "tool_recommendation", "gtn_training"],
            sequential=True,
            reasoning="Multi-step workflow: error diagnosis -> tool alternatives -> learning resources",
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

            mock_tool_agent = AsyncMock()
            mock_tool_agent.process.return_value = MagicMock(
                content="Alternative tools: HISAT2, STAR", agent_type="tool_recommendation"
            )

            mock_training_agent = AsyncMock()
            mock_training_agent.process.return_value = MagicMock(
                content="Training available: RNA-seq tutorial", agent_type="gtn_training"
            )

            # Configure mock to return different agents
            def get_agent_side_effect(agent_type, deps):
                if agent_type == "error_analysis":
                    return mock_error_agent
                elif agent_type == "tool_recommendation":
                    return mock_tool_agent
                elif agent_type == "gtn_training":
                    return mock_training_agent
                else:
                    raise ValueError(f"Unexpected agent type: {agent_type}")

            mock_get_agent.side_effect = get_agent_side_effect

            response = await agent.process(
                "My RNA-seq tool failed with memory error and I need alternatives and tutorials"
            )

            # Verify orchestration occurred
            assert response.agent_type == "orchestrator"
            assert response.metadata.get("execution_type") == "sequential"
            assert "memory issues" in response.content
            assert "Alternative tools" in response.content
            assert "Training available" in response.content

            # Verify agents were called in sequence
            assert mock_error_agent.process.called
            assert mock_tool_agent.process.called
            assert mock_training_agent.process.called

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_parallel_execution(self):
        """Test orchestrator parallel workflow execution."""
        from galaxy.agents.orchestrator import (
            AgentPlan,
            WorkflowOrchestratorAgent,
        )

        agent = WorkflowOrchestratorAgent(self.deps)

        # Mock parallel plan
        parallel_plan = AgentPlan(
            agents=["tool_recommendation", "gtn_training"],
            sequential=False,
            reasoning="Independent tasks can run in parallel",
        )

        with (
            patch.object(agent, "_get_agent_plan") as mock_get_plan,
            patch("galaxy.agents.agent_registry.get_agent") as mock_get_agent,
        ):
            mock_get_plan.return_value = parallel_plan

            # Mock agent responses
            mock_tool_agent = AsyncMock()
            mock_tool_agent.process.return_value = MagicMock(
                content="Recommended tools: BWA, Bowtie2", agent_type="tool_recommendation"
            )

            mock_training_agent = AsyncMock()
            mock_training_agent.process.return_value = MagicMock(
                content="Available tutorials: Alignment workflow", agent_type="gtn_training"
            )

            def get_agent_side_effect(agent_type, deps):
                if agent_type == "tool_recommendation":
                    return mock_tool_agent
                elif agent_type == "gtn_training":
                    return mock_training_agent
                else:
                    raise ValueError(f"Unexpected agent type: {agent_type}")

            mock_get_agent.side_effect = get_agent_side_effect

            response = await agent.process("I need alignment tools and training materials")

            # Verify parallel execution
            assert response.agent_type == "orchestrator"
            assert response.metadata.get("execution_type") == "parallel"
            assert "Recommended tools" in response.content
            assert "Available tutorials" in response.content

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
        from galaxy.agents.orchestrator import WorkflowOrchestratorAgent

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
    async def test_router_agent_routing_decisions_live(self):
        """Test router with real LLM."""
        router = QueryRouterAgent(self.deps)

        test_cases = [
            ("Create a BWA tool", "custom_tool"),
            ("Why did my job fail?", "error_analysis"),
            ("What tools can I use for RNA-seq?", "tool_recommendation"),
        ]

        for query, expected_agent in test_cases:
            decision = await router.route_query(query)
            assert (
                decision.primary_agent == expected_agent
            ), f"Query '{query}' should route to {expected_agent}, got {decision.primary_agent}"

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
    """Test agents with a consistent set of questions."""

    TEST_QUERIES = [
        # Tool creation queries
        ("Create a simple line counting tool", "custom_tool"),
        ("Build a Galaxy tool that runs samtools sort", "custom_tool"),
        ("I need a wrapper for BWA-MEM", "custom_tool"),
        # Error analysis queries
        ("Why did my job fail with exit code 127?", "error_analysis"),
        ("Help me debug this memory error", "error_analysis"),
        ("What does 'command not found' mean?", "error_analysis"),
        # Tool recommendation queries
        ("What tools can I use for RNA-seq analysis?", "tool_recommendation"),
        ("How do I convert BAM to FASTQ?", "tool_recommendation"),
        ("Which aligner should I use for short reads?", "tool_recommendation"),
        # GTN training queries
        ("Find me a tutorial on variant calling", "gtn_training"),
        ("How do I learn Galaxy basics?", "gtn_training"),
        ("Training materials for proteomics", "gtn_training"),
        # Meta queries (should get direct response)
        ("Hello", None),
        ("Thank you", None),
        ("What can you do?", None),
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
    async def test_routing_consistency_live(self, live_deps):
        """Test that routing is consistent for known query types with live LLM."""
        router = QueryRouterAgent(live_deps)

        for query, expected_agent in self.TEST_QUERIES:
            decision = await router.route_query(query)

            if expected_agent is None:
                # Should provide direct response
                assert decision.direct_response is not None, f"Query '{query}' should get direct response"
            else:
                # Should route to expected agent
                assert (
                    decision.primary_agent == expected_agent
                ), f"Query '{query}' should route to {expected_agent}, got {decision.primary_agent}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_agent", TEST_QUERIES)
    async def test_individual_query_routing_live(self, live_deps, query, expected_agent):
        """Test each query individually with live LLM."""
        router = QueryRouterAgent(live_deps)
        decision = await router.route_query(query)

        if expected_agent is None:
            assert decision.direct_response is not None
        else:
            assert decision.primary_agent == expected_agent
