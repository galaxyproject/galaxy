"""Unit tests for the runner-level ``default_<param>`` destination-seeding mechanism.

See ``BaseJobRunner._apply_runner_default_destination_params``.
"""

from unittest.mock import Mock

import pytest

from galaxy.exceptions import ConfigurationError
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners import (
    BaseJobRunner,
    RunnerParams,
)
from galaxy.jobs.runners.pulsar import (
    PULSAR_PARAM_SPECS,
    PulsarGcpBatchJobRunner,
)
from galaxy.util import specs

IMAGE_SPEC = dict(map=specs.to_str_or_none, default=None)


def _mock_app():
    app = Mock()
    app.config.redact_email_in_job_name = False
    return app


class _Runner(BaseJobRunner):
    runner_default_destination_params = ["custom_vm_image"]


def _make_runner(params, param_specs=None, runner_class=_Runner):
    """Build a runner without running __init__ (no threads, no client).

    The helper only depends on self.runner_params, which is a real RunnerParams so
    that spec-default fallback through __missing__ is exercised rather than mocked.
    """
    runner = object.__new__(runner_class)
    runner.runner_params = RunnerParams(
        specs=param_specs if param_specs is not None else {"default_custom_vm_image": IMAGE_SPEC},
        params=params,
    )
    return runner


def _apply(params, dest_params, param_specs=None, runner_class=_Runner):
    runner = _make_runner(params, param_specs=param_specs, runner_class=runner_class)
    destination = JobDestination(params=dict(dest_params))
    updated = runner._apply_runner_default_destination_params(destination)
    return updated, destination.params


def test_runner_default_seeds_unset_destination_param():
    updated, params = _apply({"default_custom_vm_image": "projects/p/global/images/cvmfs"}, {})
    assert updated is True
    assert params["custom_vm_image"] == "projects/p/global/images/cvmfs"


def test_destination_value_overrides_runner_default():
    updated, params = _apply({"default_custom_vm_image": "runner-image"}, {"custom_vm_image": "destination-image"})
    assert updated is False
    assert params["custom_vm_image"] == "destination-image"


def test_no_runner_default_leaves_destination_untouched():
    updated, params = _apply({}, {})
    assert updated is False
    assert "custom_vm_image" not in params


def test_only_listed_params_are_seeded():
    param_specs = {"default_custom_vm_image": IMAGE_SPEC, "default_other_param": IMAGE_SPEC}
    updated, params = _apply({"default_other_param": "value"}, {}, param_specs=param_specs)
    assert updated is False
    assert "other_param" not in params


def test_unset_default_falls_back_to_spec_default():
    """An unset default_<param> resolves through RunnerParams.__missing__, not to None.

    This is the regression guard: .get() on the RunnerParams defaultdict would bypass
    __missing__ and yield None, so a spec default would never reach the destination.
    """
    param_specs = {"default_custom_vm_image": dict(map=specs.to_str_or_none, default="spec-default-image")}
    updated, params = _apply({}, {}, param_specs=param_specs)
    assert updated is True
    assert params["custom_vm_image"] == "spec-default-image"


@pytest.mark.parametrize("value", [False, 0, ""])
def test_falsy_runner_default_is_still_applied(value):
    """Only None means "unset" - an explicitly configured falsy value is a real value."""

    class _FalsyRunner(BaseJobRunner):
        runner_default_destination_params = ["use_container"]

    param_specs = {"default_use_container": dict(map=lambda x: x, default=None)}
    runner = _make_runner({"default_use_container": value}, param_specs=param_specs, runner_class=_FalsyRunner)
    destination = JobDestination(params={})

    assert runner._apply_runner_default_destination_params(destination) is True
    assert destination.params["use_container"] == value


def test_destination_falsy_value_beats_runner_default():
    updated, params = _apply({"default_custom_vm_image": "runner-image"}, {"custom_vm_image": None})
    assert updated is False
    assert params["custom_vm_image"] is None


def test_seeding_is_idempotent():
    """Runners that also call the hook directly must not be penalized for double-applying."""
    runner = _make_runner({"default_custom_vm_image": "runner-image"})
    destination = JobDestination(params={})

    assert runner._apply_runner_default_destination_params(destination) is True
    assert runner._apply_runner_default_destination_params(destination) is False
    assert destination.params["custom_vm_image"] == "runner-image"


class TestDeclarationValidation:
    """A listed param with no matching default_<param> spec must fail loudly at startup."""

    def test_missing_spec_is_a_configuration_error(self):
        class _MisdeclaredRunner(BaseJobRunner):
            runner_name = "MisdeclaredRunner"
            runner_default_destination_params = ["never_registered"]

        with pytest.raises(ConfigurationError, match="never_registered"):
            _MisdeclaredRunner(_mock_app(), 1)

    def test_registered_spec_starts_cleanly(self):
        class _DeclaredRunner(BaseJobRunner):
            runner_name = "DeclaredRunner"
            runner_default_destination_params = ["custom_vm_image"]

        runner = _DeclaredRunner(_mock_app(), 1, runner_param_specs={"default_custom_vm_image": IMAGE_SPEC})
        assert runner.runner_params["default_custom_vm_image"] is None


class TestPulsarGcpBatchWiring:
    """The GCP Batch runner's declaration, spec registration and hook must line up."""

    def test_declared_default_is_registered_in_param_specs(self):
        for name in PulsarGcpBatchJobRunner.runner_default_destination_params:
            assert f"default_{name}" in PULSAR_PARAM_SPECS

    def test_legacy_runner_level_name_is_rejected(self):
        """The pre-rename key must be an unknown param, not a silently ignored one."""
        assert "custom_vm_image" not in PULSAR_PARAM_SPECS

    def test_populate_parameter_defaults_seeds_through_the_pulsar_hook(self):
        runner = _make_runner(
            {"default_custom_vm_image": "projects/p/global/images/cvmfs"},
            param_specs=PULSAR_PARAM_SPECS,
            runner_class=PulsarGcpBatchJobRunner,
        )
        destination = JobDestination(params={"project_id": "p", "url": "http://localhost"})

        runner._populate_parameter_defaults(destination)

        assert destination.params["custom_vm_image"] == "projects/p/global/images/cvmfs"
