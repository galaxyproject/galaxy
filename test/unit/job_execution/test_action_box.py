"""Tests for dispatching post job actions to step outputs with no job."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

from galaxy.job_execution.actions.post import (
    ActionBox,
    DefaultJobAction,
)


def _all_action_classes():
    def descend(action_class):
        yield action_class
        for subclass in action_class.__subclasses__():
            yield from descend(subclass)

    return list(descend(DefaultJobAction))


def _implements_mapped_over(action_class):
    return action_class.execute_on_mapped_over.__func__ is not DefaultJobAction.execute_on_mapped_over.__func__


def test_supports_mapped_over_matches_implementation():
    """supports_mapped_over has to agree with what the class actually overrides.

    ActionBox skips and warns about actions that do not set it, so a stale flag
    either drops a working action or lets an unimplemented one through as a
    no-op - which is what the flag exists to make noisy.
    """
    for action_class in _all_action_classes():
        assert action_class.supports_mapped_over == _implements_mapped_over(action_class), action_class.name


def test_mapped_over_output_actions_are_supported():
    """Every action ToolModule applies to mapped over outputs must implement it."""
    for action_type in ActionBox.mapped_over_output_actions:
        assert ActionBox.actions[action_type].supports_mapped_over, action_type


def _dispatch(action_type, step_outputs):
    pja = Mock(
        action_type=action_type,
        output_name="",
        workflow_step_id=1,
        action_arguments={"newname": "renamed"},
    )
    ActionBox.execute_on_mapped_over(Mock(), Mock(), pja, {}, step_outputs)


def _warnings(caplog):
    return [record for record in caplog.records if record.levelno >= logging.WARNING]


def test_unsupported_action_warns_instead_of_running(caplog):
    """EmailAction is configurable on a pick_value step but has no job to report on."""
    _dispatch("EmailAction", {})
    assert [record for record in _warnings(caplog) if "EmailAction" in record.getMessage()]


def test_supported_action_still_runs(caplog):
    """The rename has to actually reach the output, not just avoid the warning."""
    output = SimpleNamespace(name="original")
    _dispatch("RenameDatasetAction", {"output": output})
    assert output.name == "renamed"
    assert _warnings(caplog) == []


def test_unknown_action_is_ignored(caplog):
    _dispatch("NoSuchAction", {})
    assert _warnings(caplog) == []
