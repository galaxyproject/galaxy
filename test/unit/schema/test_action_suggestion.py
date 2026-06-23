"""Unit tests for ActionSuggestion parameter validation."""

import pytest

from galaxy.schema.agents import (
    ActionSuggestion,
    ActionType,
    ConfidenceLevel,
)


class TestActionSuggestionValidation:
    """Test ActionSuggestion validates required parameters per action type."""

    def test_tool_run_requires_tool_id(self):
        """TOOL_RUN action must have a tool_id parameter."""
        with pytest.raises(ValueError, match="tool_id"):
            ActionSuggestion(
                action_type=ActionType.TOOL_RUN,
                description="Open tool",
                confidence=ConfidenceLevel.HIGH,
            )

    def test_tool_run_rejects_empty_tool_id(self):
        """TOOL_RUN rejects empty string tool_id."""
        with pytest.raises(ValueError, match="tool_id"):
            ActionSuggestion(
                action_type=ActionType.TOOL_RUN,
                description="Open tool",
                parameters={"tool_id": ""},
                confidence=ConfidenceLevel.HIGH,
            )

    def test_tool_run_accepts_valid_params(self):
        """TOOL_RUN accepts valid tool_id parameter."""
        s = ActionSuggestion(
            action_type=ActionType.TOOL_RUN,
            description="Open BWA",
            parameters={"tool_id": "bwa"},
            confidence=ConfidenceLevel.HIGH,
        )
        assert s.parameters["tool_id"] == "bwa"

    def test_save_tool_requires_tool_yaml(self):
        """SAVE_TOOL action must have a tool_yaml parameter."""
        with pytest.raises(ValueError, match="tool_yaml"):
            ActionSuggestion(
                action_type=ActionType.SAVE_TOOL,
                description="Save tool",
                confidence=ConfidenceLevel.HIGH,
            )

    def test_save_tool_rejects_empty_tool_yaml(self):
        """SAVE_TOOL rejects empty string tool_yaml."""
        with pytest.raises(ValueError, match="tool_yaml"):
            ActionSuggestion(
                action_type=ActionType.SAVE_TOOL,
                description="Save tool",
                parameters={"tool_yaml": ""},
                confidence=ConfidenceLevel.HIGH,
            )

    def test_save_tool_accepts_valid_params(self):
        """SAVE_TOOL accepts valid tool_yaml parameter."""
        yaml_content = "id: test\nname: Test Tool"
        s = ActionSuggestion(
            action_type=ActionType.SAVE_TOOL,
            description="Save the tool",
            parameters={"tool_yaml": yaml_content, "tool_id": "test"},
            confidence=ConfidenceLevel.HIGH,
        )
        assert s.parameters["tool_yaml"] == yaml_content
        assert s.parameters["tool_id"] == "test"

    def test_view_external_requires_url(self):
        """VIEW_EXTERNAL action must have a url parameter."""
        with pytest.raises(ValueError, match="url"):
            ActionSuggestion(
                action_type=ActionType.VIEW_EXTERNAL,
                description="View docs",
                confidence=ConfidenceLevel.HIGH,
            )

    def test_view_external_rejects_empty_url(self):
        """VIEW_EXTERNAL rejects empty string url."""
        with pytest.raises(ValueError, match="url"):
            ActionSuggestion(
                action_type=ActionType.VIEW_EXTERNAL,
                description="View docs",
                parameters={"url": ""},
                confidence=ConfidenceLevel.HIGH,
            )

    def test_view_external_accepts_valid_params(self):
        """VIEW_EXTERNAL accepts valid url parameter."""
        s = ActionSuggestion(
            action_type=ActionType.VIEW_EXTERNAL,
            description="View Galaxy training",
            parameters={"url": "https://training.galaxyproject.org"},
            confidence=ConfidenceLevel.HIGH,
        )
        assert s.parameters["url"] == "https://training.galaxyproject.org"

    def test_contact_support_no_params_required(self):
        """CONTACT_SUPPORT does not require any parameters."""
        s = ActionSuggestion(
            action_type=ActionType.CONTACT_SUPPORT,
            description="Get help",
            confidence=ConfidenceLevel.HIGH,
        )
        assert s.parameters == {}

    def test_documentation_no_params_required(self):
        """DOCUMENTATION does not require any parameters."""
        s = ActionSuggestion(
            action_type=ActionType.DOCUMENTATION,
            description="Read the docs",
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert s.parameters == {}

    def test_priority_defaults_to_one(self):
        """Priority defaults to 1 when not specified."""
        s = ActionSuggestion(
            action_type=ActionType.CONTACT_SUPPORT,
            description="Get help",
            confidence=ConfidenceLevel.HIGH,
        )
        assert s.priority == 1

    def test_accepts_custom_priority(self):
        """Custom priority values are accepted."""
        s = ActionSuggestion(
            action_type=ActionType.DOCUMENTATION,
            description="Low priority docs",
            confidence=ConfidenceLevel.LOW,
            priority=3,
        )
        assert s.priority == 3
