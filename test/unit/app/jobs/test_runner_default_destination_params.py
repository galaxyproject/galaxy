"""Unit tests for the runner-level ``default_<param>`` destination-seeding mechanism.

See ``BaseJobRunner._apply_runner_default_destination_params``.
"""

from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners import BaseJobRunner


class _StubRunner(BaseJobRunner):
    """Minimal runner that bypasses ``BaseJobRunner.__init__`` for the helper under test."""

    def __init__(self, runner_params, defaultable):
        self.runner_params = runner_params
        self.runner_default_destination_params = defaultable


def _apply(runner_params, defaultable, dest_params):
    runner = _StubRunner(runner_params, defaultable)
    destination = JobDestination(params=dict(dest_params))
    updated = runner._apply_runner_default_destination_params(destination)
    return updated, destination.params


def test_runner_default_seeds_unset_destination_param():
    updated, params = _apply(
        runner_params={"default_custom_vm_image": "projects/p/global/images/cvmfs"},
        defaultable=["custom_vm_image"],
        dest_params={},
    )
    assert updated is True
    assert params["custom_vm_image"] == "projects/p/global/images/cvmfs"


def test_destination_value_overrides_runner_default():
    updated, params = _apply(
        runner_params={"default_custom_vm_image": "runner-image"},
        defaultable=["custom_vm_image"],
        dest_params={"custom_vm_image": "destination-image"},
    )
    assert updated is False
    assert params["custom_vm_image"] == "destination-image"


def test_no_runner_default_leaves_destination_untouched():
    updated, params = _apply(
        runner_params={},
        defaultable=["custom_vm_image"],
        dest_params={},
    )
    assert updated is False
    assert "custom_vm_image" not in params


def test_falsy_runner_default_is_ignored():
    updated, params = _apply(
        runner_params={"default_custom_vm_image": ""},
        defaultable=["custom_vm_image"],
        dest_params={},
    )
    assert updated is False
    assert "custom_vm_image" not in params


def test_only_listed_params_are_seeded():
    updated, params = _apply(
        runner_params={"default_other_param": "value"},
        defaultable=["custom_vm_image"],
        dest_params={},
    )
    assert updated is False
    assert "other_param" not in params
