"""Unit tests for the Teaching Assistant agent and learning state management."""

import json
from types import SimpleNamespace
from unittest import mock

import pytest

pydantic_ai = pytest.importorskip("pydantic_ai")

from galaxy.agents import (
    AgentType,
    GalaxyAgentDependencies,
)
from galaxy.agents.base import JOB_LOG_EXCERPT_CHARS
from galaxy.agents.registry import build_default_registry
from galaxy.agents.teaching_assistant import (
    _render_tutorial_references,
    TeachingAssistantAgent,
)

agent_registry = build_default_registry()
from galaxy.managers.learning_state import (
    DEFAULT_LEARNING_STATE,
    LearningStateManager,
)
from galaxy.schema.agents import (
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
        assert "Scaffolding level" in prompt

    def test_build_learning_context_default(self):
        """Learning context should expose support preferences without inferring competence."""
        agent = TeachingAssistantAgent(self.deps)
        context = agent._build_learning_context()
        assert "Scaffolding level:** 3" in context
        assert "expertise" not in context.lower()

    def test_tutor_specific_fallback(self):
        """Fallback message should mention training.galaxyproject.org."""
        agent = TeachingAssistantAgent(self.deps)
        fallback = agent._get_fallback_content()
        assert "training.galaxyproject.org" in fallback

    @pytest.mark.parametrize("job_id", [123, "encoded-job"])
    def test_prompt_exposes_encoded_job_id(self, job_id):
        self.mock_trans.security.encode_id.return_value = "encoded-job"
        agent = TeachingAssistantAgent(self.deps)
        context = {"job_id": job_id}

        prompt = agent._prepare_prompt("Help me understand this failure", context)

        assert "job_id: encoded-job" in prompt
        assert context["job_id"] == job_id
        if isinstance(job_id, int):
            self.mock_trans.security.encode_id.assert_called_once_with(job_id)
        else:
            self.mock_trans.security.encode_id.assert_not_called()

    @pytest.mark.parametrize("log_prefix", ["", "HISAT2 starting\n" + "progress\n" * 1000])
    async def test_error_analysis_passes_stderr_to_specialist(self, log_prefix):
        agent = TeachingAssistantAgent(self.deps)
        stderr = log_prefix + "No index found"
        agent.ops.get_job_status = mock.Mock(
            return_value={"job": {"tool_id": "hisat2", "state": "error", "exit_code": 1, "stderr": stderr}}
        )
        agent._call_agent_from_tool = mock.AsyncMock(return_value="Check which reference index was selected.")
        ctx = mock.Mock()

        result = await agent.agent._function_toolset.tools["analyze_error"].function(ctx, "encoded-job")

        agent.ops.get_job_status.assert_called_once_with("encoded-job", full=True)
        assert "No index found" in result
        delegated_query = agent._call_agent_from_tool.call_args.args[1]
        assert "No index found" in delegated_query
        assert len(delegated_query.split("stderr=", 1)[1]) <= JOB_LOG_EXCERPT_CHARS
        if log_prefix:
            assert "HISAT2 starting" in result
            assert "HISAT2 starting" in delegated_query
        assert "Check which reference index was selected." in result

    def test_prompt_excludes_internal_routing_state(self):
        agent = TeachingAssistantAgent(self.deps)
        context = {
            "history_name": "RNA-seq practice",
            "run_state": "internal execution bookkeeping",
            "responding_to_clarification": True,
            "conversation_history": [{"role": "user", "content": "prior question"}],
        }

        prompt = agent._prepare_prompt("Help me interpret the results", context)

        assert "RNA-seq practice" in prompt
        assert "Help me interpret the results" in prompt
        assert "internal execution bookkeeping" not in prompt
        assert "responding_to_clarification" not in prompt
        assert "prior question" not in prompt

    def test_agent_has_tools(self):
        """The pydantic-ai agent should have registered tools."""
        agent = TeachingAssistantAgent(self.deps)
        toolset = agent.agent._function_toolset
        tool_names = list(toolset.tools.keys())
        assert "search_training_materials" in tool_names
        assert "suggest_tutorials" in tool_names
        assert "check_user_context" in tool_names
        assert "analyze_error" in tool_names
        assert "recommend_tools" in tool_names
        assert "demonstrate_concept" in tool_names
        assert "save_learning_note" not in tool_names

    @pytest.mark.parametrize("tool_name", ["search_training_materials", "suggest_tutorials"])
    async def test_search_failure_is_not_an_empty_result(self, tool_name):
        agent = TeachingAssistantAgent(self.deps)
        agent.gtn_db = mock.Mock()
        agent.gtn_db.search.side_effect = RuntimeError("private database path")

        result = await agent.agent._function_toolset.tools[tool_name].function(mock.Mock(), "RNA-seq")

        assert "search failed" in result
        assert "availability is unknown" in result
        assert "private database path" not in result

    def test_source_records_preserve_distinct_excerpts_and_escape_markdown(self):
        agent = TeachingAssistantAgent(self.deps)
        record = {"title": "Quality [control]", "url": "https://training.galaxyproject.org/qc"}
        first = mock.Mock(difficulty="introductory")
        first.to_dict.return_value = {**record, "snippet": "First excerpt."}
        second = mock.Mock(difficulty="advanced")
        second.to_dict.return_value = {
            **record,
            "snippet": "[invented](https://example.org) <b>text</b> https://example.org [[tutorial:000000000000]]",
        }
        agent.gtn_db = mock.Mock()
        agent.gtn_db.search.return_value = [second, first]
        result = agent._search_tutorials("QC", 8, easiest_first=True)
        sources = result.metadata["tutor_sources"]
        assert sources[0]["excerpt"] == "First excerpt."
        assert sources[0]["id"] != sources[1]["id"]
        part = SimpleNamespace(part_kind="tool-return", tool_name="suggest_tutorials", metadata=result.metadata)
        ctx = SimpleNamespace(run_id="current", messages=[SimpleNamespace(run_id="current", parts=[part])])
        rendered = _render_tutorial_references(ctx, f"[[tutorial:{sources[1]['id']}]]")
        assert "[Quality \\[control\\]](<https://training.galaxyproject.org/qc>)" in rendered
        assert "[invented](" not in rendered
        assert "<b>" not in rendered
        assert "https://example.org" not in rendered
        assert "[[tutorial:" not in rendered
        marker = f"[[tutorial:{sources[0]['id']}]]"
        rendered = _render_tutorial_references(ctx, marker + "\nMy own explanation.")
        assert "> First excerpt\\.\n\n\nMy own explanation." in rendered
        for misplaced in [f"See {marker}", f"```\n{marker}\n```", f"    {marker}"]:
            with pytest.raises(pydantic_ai.ModelRetry):
                _render_tutorial_references(ctx, misplaced)

    @pytest.mark.parametrize("tool_name, run_id", [("recommend_tools", "current"), ("suggest_tutorials", None)])
    def test_only_current_search_records_authorize_references(self, tool_name, run_id):
        part = SimpleNamespace(
            part_kind="tool-return",
            tool_name=tool_name,
            metadata={"tutor_sources": [{"id": "000000000000", "title": "Invented"}]},
        )
        ctx = SimpleNamespace(run_id=run_id, messages=[SimpleNamespace(run_id=run_id, parts=[part])])
        with pytest.raises(pydantic_ai.ModelRetry):
            _render_tutorial_references(ctx, "[[tutorial:000000000000]]")


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
        assert state["scaffolding_level"] == 3
        assert state["interaction_count"] == 0
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
            "interaction_count": 42,
            "tutor_mode_enabled": True,
        }
        self.mock_user.preferences = {"learning_state": json.dumps(saved_state)}

        state = self.manager.get_learning_state(self.mock_trans)
        assert "expertise_level" not in state
        assert state["scaffolding_level"] == 2
        assert state["interaction_count"] == 42
        assert state["tutor_mode_enabled"] is True
        # Should merge with defaults for missing keys
        assert "demonstrations_count" in state

    @pytest.mark.parametrize("preference", ["not valid json{{", "[]", "null"])
    def test_corrupted_json_returns_defaults(self, preference):
        """Should handle corrupted JSON gracefully."""
        self.mock_user.preferences = {"learning_state": preference}

        state = self.manager.get_learning_state(self.mock_trans)
        assert state == DEFAULT_LEARNING_STATE

    def test_enable_tutor_mode(self):
        """Should enable tutor mode."""
        state = self.manager.enable_tutor_mode(self.mock_trans)
        assert state["tutor_mode_enabled"] is True

    def test_disable_tutor_mode(self):
        """Should disable tutor mode."""
        state = self.manager.disable_tutor_mode(self.mock_trans)
        assert state["tutor_mode_enabled"] is False

    def test_record_interaction(self):
        """Should increment interaction count."""
        state = self.manager.record_interaction(self.mock_trans)
        assert state["interaction_count"] == 1
        assert state["last_interaction"] is not None

    @pytest.mark.parametrize("count", [29, 99])
    def test_record_interaction_does_not_infer_expertise(self, count):
        saved = dict(DEFAULT_LEARNING_STATE)
        saved["interaction_count"] = count
        saved["expertise_level"] = "advanced"
        self.mock_user.preferences = {"learning_state": json.dumps(saved)}

        state = self.manager.record_interaction(self.mock_trans)
        assert state["interaction_count"] == count + 1
        assert "expertise_level" not in state
        assert "expertise_level" not in json.loads(self.mock_user.preferences["learning_state"])

    def test_record_demonstration(self):
        """Should increment the count of submitted demonstration runs."""
        state = self.manager.record_demonstration(self.mock_trans)
        assert state["demonstrations_count"] == 1


class TestSchemaAdditions:
    """Test new schema types for the tutor."""

    def test_learning_state_defaults(self):
        """LearningState should have sensible defaults."""
        state = LearningState()
        assert state.scaffolding_level == 3
        assert state.tutor_mode_enabled is False

    def test_learning_state_from_dict(self):
        """LearningState should parse from dict."""
        data = {
            "expertise_level": "advanced",
            "scaffolding_level": 5,
            "interaction_count": 120,
            "tutor_mode_enabled": True,
        }
        state = LearningState(**data)
        assert "expertise_level" not in state.model_dump()
        assert state.interaction_count == 120

    def test_tutor_mode_toggle(self):
        """TutorModeToggle should validate."""
        toggle = TutorModeToggle(enabled=True)
        assert toggle.enabled is True


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

    @pytest.mark.parametrize("enabled", [None, False, True])
    async def test_demonstration_only_executes_and_counts_when_enabled(self, enabled):
        if enabled is None:
            del self.mock_config.tutor_allow_tool_execution
        else:
            self.mock_config.tutor_allow_tool_execution = enabled
        self.mock_trans.get_history.return_value = mock.Mock(id=23)
        self.mock_trans.security.encode_id.return_value = "history-23"
        agent = TeachingAssistantAgent(self.deps)
        agent.ops = mock.Mock()
        agent.ops.get_tool_details.return_value = {"id": "fastqc", "name": "FastQC"}
        agent.ops.run_tool.return_value = {"jobs": [{"id": "job-1"}]}

        await agent.agent._function_toolset.tools["demonstrate_concept"].function(mock.Mock(), "fastqc", "{}")

        if enabled:
            agent.ops.run_tool.assert_called_once_with("history-23", "fastqc", {})
            agent.ops.get_tool_details.assert_not_called()
        else:
            agent.ops.run_tool.assert_not_called()
            agent.ops.get_tool_details.assert_called_once_with("fastqc", io_details=True)
        state = agent.learning_state_manager.get_learning_state(self.mock_trans)
        assert state["demonstrations_count"] == (1 if enabled else 0)

    @pytest.mark.parametrize("failure", [RuntimeError("Tool unavailable"), None])
    async def test_demonstration_without_submitted_jobs_does_not_count(self, failure):
        self.mock_config.tutor_allow_tool_execution = True
        self.mock_trans.get_history.return_value = mock.Mock(id=23)
        self.mock_trans.security.encode_id.return_value = "history-23"
        agent = TeachingAssistantAgent(self.deps)
        agent.ops = mock.Mock()
        agent.ops.run_tool.side_effect = failure
        agent.ops.run_tool.return_value = {"jobs": []}

        result = await agent.agent._function_toolset.tools["demonstrate_concept"].function(mock.Mock(), "fastqc", "{}")

        assert ("Could not run tool" if failure else "No demonstration jobs were submitted") in result
        assert agent.learning_state_manager.get_learning_state(self.mock_trans)["demonstrations_count"] == 0
