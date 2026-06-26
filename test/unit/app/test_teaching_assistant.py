"""Unit tests for the Teaching Assistant agent and learning state management."""

import json
from unittest import mock

import pytest

pydantic_ai = pytest.importorskip("pydantic_ai")

from galaxy.agents import (
    AgentType,
    GalaxyAgentDependencies,
)
from galaxy.agents.registry import build_default_registry
from galaxy.agents.teaching_assistant import TeachingAssistantAgent

agent_registry = build_default_registry()
from galaxy.managers.learning_state import (
    DEFAULT_LEARNING_STATE,
    LearningStateManager,
)
from galaxy.schema.agents import (
    ActionType,
    LearningState,
    TutorModeToggle,
)


class TestTeachingAssistantRegistration:
    """Test that the teaching assistant is properly registered."""

    def test_agent_registered(self):
        """Teaching assistant should be in the registry."""
        assert agent_registry.is_registered(AgentType.TEACHING_ASSISTANT)
        assert "teaching_assistant" in agent_registry.list_agents()

    def test_agent_type_constant(self):
        """AgentType should have TEACHING_ASSISTANT constant."""
        assert AgentType.TEACHING_ASSISTANT == "teaching_assistant"

    def test_agent_info(self):
        """Agent info should be retrievable."""
        info = agent_registry.get_agent_info(AgentType.TEACHING_ASSISTANT)
        assert info["class_name"] == "TeachingAssistantAgent"


class TestTeachingAssistantAgent:
    """Unit tests for TeachingAssistantAgent with mocked LLM."""

    def setup_method(self):
        self.mock_config = mock.Mock()
        self.mock_config.ai_api_key = "test-key"
        self.mock_config.ai_model = "gpt-4o-mini"
        self.mock_config.ai_api_base_url = "http://localhost:4000/v1/"
        self.mock_config.inference_services = {}

        self.mock_user = mock.Mock()
        self.mock_user.id = 1
        self.mock_user.username = "test_learner"
        self.mock_user.preferences = {}

        self.mock_trans = mock.Mock()
        self.mock_trans.app.config = self.mock_config
        self.mock_trans.user = self.mock_user
        self.mock_trans.get_history.return_value = None

        self.deps = GalaxyAgentDependencies(
            trans=self.mock_trans,
            user=self.mock_user,
            config=self.mock_config,
            get_agent=mock.Mock(),
        )

    def test_agent_creation(self):
        """Teaching assistant agent should be created successfully."""
        agent = TeachingAssistantAgent(self.deps)
        assert agent.agent_type == "teaching_assistant"
        assert agent.learning_state_manager is not None
        assert agent.ops is not None
        # gtn_db is optional (degrades to None when the GTN database is unavailable)
        assert hasattr(agent, "gtn_db")

    def test_system_prompt_contains_pedagogy(self):
        """System prompt should contain pedagogical instructions."""
        agent = TeachingAssistantAgent(self.deps)
        prompt = agent.get_system_prompt()
        assert "Socratic" in prompt
        assert "scaffolding" in prompt.lower()
        assert "demonstrate" in prompt.lower()
        assert "learning" in prompt.lower()

    def test_system_prompt_includes_learning_context(self):
        """System prompt should inject learning state context."""
        agent = TeachingAssistantAgent(self.deps)
        prompt = agent.get_system_prompt()
        # Default state should be injected
        assert "beginner" in prompt
        assert "Scaffolding level" in prompt

    def test_build_learning_context_default(self):
        """Default learning context should reflect beginner state."""
        agent = TeachingAssistantAgent(self.deps)
        context = agent._build_learning_context()
        assert "beginner" in context
        assert "3" in context  # default scaffolding level

    def test_tutor_specific_fallback(self):
        """Fallback message should mention training.galaxyproject.org."""
        agent = TeachingAssistantAgent(self.deps)
        fallback = agent._get_fallback_content()
        assert "training.galaxyproject.org" in fallback

    def test_agent_has_tools(self):
        """The pydantic-ai agent should have registered tools."""
        agent = TeachingAssistantAgent(self.deps)
        toolset = agent.agent._function_toolset
        tool_names = list(toolset.tools.keys())
        assert "search_training_materials" in tool_names
        assert "get_learning_pathway" in tool_names
        assert "check_user_context" in tool_names
        assert "analyze_error" in tool_names
        assert "recommend_tools" in tool_names
        assert "demonstrate_concept" in tool_names
        assert "save_learning_note" in tool_names


class TestLearningStateManager:
    """Unit tests for LearningStateManager."""

    def setup_method(self):
        self.manager = LearningStateManager()

        # Mock user with preferences list
        self.mock_user = mock.Mock()
        self.mock_user.id = 1
        self.mock_user.preferences = {}

        self.mock_trans = mock.Mock()
        self.mock_trans.user = self.mock_user
        self.mock_trans.sa_session = mock.Mock()

    def test_get_default_state(self):
        """Should return default state when no preference exists."""
        state = self.manager.get_learning_state(self.mock_trans)
        assert state["expertise_level"] == "beginner"
        assert state["scaffolding_level"] == 3
        assert state["completed_tutorials"] == []
        assert state["tutor_mode_enabled"] is False

    def test_get_state_no_user(self):
        """Should return default state when no user is logged in."""
        self.mock_trans.user = None
        state = self.manager.get_learning_state(self.mock_trans)
        assert state == DEFAULT_LEARNING_STATE

    def test_get_state_from_preference(self):
        """Should deserialize state from UserPreference."""
        saved_state = {
            "expertise_level": "intermediate",
            "scaffolding_level": 2,
            "completed_tutorials": ["intro/galaxy-intro-short"],
            "tutor_mode_enabled": True,
        }
        self.mock_user.preferences = {"learning_state": json.dumps(saved_state)}

        state = self.manager.get_learning_state(self.mock_trans)
        assert state["expertise_level"] == "intermediate"
        assert state["scaffolding_level"] == 2
        assert state["completed_tutorials"] == ["intro/galaxy-intro-short"]
        assert state["tutor_mode_enabled"] is True
        # Should merge with defaults for missing keys
        assert "interaction_count" in state

    def test_corrupted_json_returns_defaults(self):
        """Should handle corrupted JSON gracefully."""
        self.mock_user.preferences = {"learning_state": "not valid json{{"}

        state = self.manager.get_learning_state(self.mock_trans)
        assert state == DEFAULT_LEARNING_STATE

    def test_adjust_scaffolding_up(self):
        """Should increase scaffolding level (less support)."""
        state = self.manager.adjust_scaffolding(self.mock_trans, "up")
        assert state["scaffolding_level"] == 4  # default 3 + 1

    def test_adjust_scaffolding_down(self):
        """Should decrease scaffolding level (more support)."""
        state = self.manager.adjust_scaffolding(self.mock_trans, "down")
        assert state["scaffolding_level"] == 2  # default 3 - 1

    def test_scaffolding_clamped_at_bounds(self):
        """Should not exceed 1-5 bounds."""
        # Set to max
        saved = dict(DEFAULT_LEARNING_STATE)
        saved["scaffolding_level"] = 5
        self.mock_user.preferences = {"learning_state": json.dumps(saved)}

        state = self.manager.adjust_scaffolding(self.mock_trans, "up")
        assert state["scaffolding_level"] == 5  # stays at 5

    def test_enable_tutor_mode(self):
        """Should enable tutor mode."""
        state = self.manager.enable_tutor_mode(self.mock_trans)
        assert state["tutor_mode_enabled"] is True

    def test_disable_tutor_mode(self):
        """Should disable tutor mode."""
        state = self.manager.disable_tutor_mode(self.mock_trans)
        assert state["tutor_mode_enabled"] is False

    def test_record_tutorial_completion(self):
        """Should track completed tutorials."""
        state = self.manager.record_tutorial_completion(self.mock_trans, "transcriptomics/ref-based", topic="rna-seq")
        assert "transcriptomics/ref-based" in state["completed_tutorials"]
        assert "rna-seq" in state["topics_explored"]

    def test_duplicate_tutorial_not_added(self):
        """Should not duplicate completed tutorials."""
        saved = dict(DEFAULT_LEARNING_STATE)
        saved["completed_tutorials"] = ["intro/galaxy-intro-short"]
        self.mock_user.preferences = {"learning_state": json.dumps(saved)}

        state = self.manager.record_tutorial_completion(self.mock_trans, "intro/galaxy-intro-short")
        assert state["completed_tutorials"].count("intro/galaxy-intro-short") == 1

    def test_expertise_inference_beginner(self):
        """Should infer beginner for few completions."""
        level = self.manager.get_expertise_level(self.mock_trans)
        assert level == "beginner"

    def test_expertise_inference_progression(self):
        """Expertise should progress based on completions."""
        saved = dict(DEFAULT_LEARNING_STATE)
        saved["completed_tutorials"] = [f"tutorial_{i}" for i in range(4)]
        saved["interaction_count"] = 35
        self.mock_user.preferences = {"learning_state": json.dumps(saved)}

        # After recording another completion, should trigger intermediate
        state = self.manager.record_tutorial_completion(self.mock_trans, "new_tutorial")
        assert state["expertise_level"] == "intermediate"

    def test_record_interaction(self):
        """Should increment interaction count."""
        state = self.manager.record_interaction(self.mock_trans)
        assert state["interaction_count"] == 1
        assert state["last_interaction"] is not None

    def test_set_current_pathway(self):
        """Should set the current learning pathway."""
        state = self.manager.set_current_pathway(self.mock_trans, "transcriptomics")
        assert state["current_pathway"] == "transcriptomics"


class TestSchemaAdditions:
    """Test new schema types for the tutor."""

    def test_learning_state_defaults(self):
        """LearningState should have sensible defaults."""
        state = LearningState()
        assert state.expertise_level == "beginner"
        assert state.scaffolding_level == 3
        assert state.tutor_mode_enabled is False

    def test_learning_state_from_dict(self):
        """LearningState should parse from dict."""
        data = {
            "expertise_level": "advanced",
            "scaffolding_level": 5,
            "completed_tutorials": ["a", "b"],
            "tutor_mode_enabled": True,
        }
        state = LearningState(**data)
        assert state.expertise_level == "advanced"
        assert len(state.completed_tutorials) == 2

    def test_tutor_mode_toggle(self):
        """TutorModeToggle should validate."""
        toggle = TutorModeToggle(enabled=True)
        assert toggle.enabled is True

    def test_new_action_types(self):
        """New action types should be defined."""
        assert ActionType.START_TUTORIAL == "start_tutorial"
        assert ActionType.NEXT_PATHWAY_STEP == "next_pathway_step"


class TestTeachingAssistantWiring:
    """Test that the tutor is wired to the real operations and GTN search."""

    def setup_method(self):
        self.mock_config = mock.Mock()
        self.mock_config.ai_api_key = "test-key"
        self.mock_config.ai_model = "gpt-4o-mini"
        self.mock_config.ai_api_base_url = "http://localhost:4000/v1/"
        self.mock_config.inference_services = {}
        # No real GTN database available in unit tests -> tutor degrades to coaching-only.
        self.mock_config.gtn_database_path = None
        self.mock_config.gtn_database_url = None

        self.mock_user = mock.Mock()
        self.mock_user.id = 1
        self.mock_user.preferences = {}

        self.mock_trans = mock.Mock()
        self.mock_trans.app.config = self.mock_config
        self.mock_trans.user = self.mock_user
        self.mock_trans.get_history.return_value = None

        self.deps = GalaxyAgentDependencies(
            trans=self.mock_trans,
            user=self.mock_user,
            config=self.mock_config,
            get_agent=mock.Mock(),
        )

    def test_real_dependencies_importable(self):
        """The real operations manager and GTN search the tutor wires to must exist."""
        from galaxy.agents.gtn import GTNSearchDB  # noqa: F401
        from galaxy.agents.operations import AgentOperationsManager  # noqa: F401

    def test_agent_uses_real_operations_manager(self):
        """The tutor should construct the real AgentOperationsManager, not a stub."""
        from galaxy.agents.operations import AgentOperationsManager

        agent = TeachingAssistantAgent(self.deps)
        assert isinstance(agent.ops, AgentOperationsManager)

    def test_agent_degrades_when_gtn_unavailable(self):
        """If the GTN database fails to load, the tutor degrades gracefully (gtn_db is None)."""
        with mock.patch(
            "galaxy.agents.teaching_assistant.GTNSearchDB",
            side_effect=RuntimeError("no database"),
        ):
            agent = TeachingAssistantAgent(self.deps)
        assert agent.gtn_db is None

    def test_no_stub_modules_remain(self):
        """The stub package should be gone after the de-stub rewire."""
        with pytest.raises(ImportError):
            __import__("galaxy.agents.stubs")

    def test_tool_execution_gated_off_by_default(self):
        """demonstrate_concept must not run tools unless explicitly enabled."""
        self.mock_config.tutor_allow_tool_execution = False
        agent = TeachingAssistantAgent(self.deps)
        assert agent._tool_execution_allowed() is False

    def test_tool_execution_can_be_enabled(self):
        """Trusted deployments can opt in to live tool execution."""
        self.mock_config.tutor_allow_tool_execution = True
        agent = TeachingAssistantAgent(self.deps)
        assert agent._tool_execution_allowed() is True
