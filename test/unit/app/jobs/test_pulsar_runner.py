"""Unit tests for Pulsar job runner utility methods."""

from types import SimpleNamespace

from galaxy.jobs.runners.pulsar import PulsarJobRunner


def _container(container_id):
    return SimpleNamespace(container_id=container_id)


class _ComputeEnvironment:
    """Minimal stand-in exposing only unstructured_path_rewrite."""

    def __init__(self, rewrites):
        self._rewrites = rewrites

    def unstructured_path_rewrite(self, path):
        return self._rewrites.get(path)


IMAGE = "/cvmfs/singularity.galaxyproject.org/all/img"
REWRITTEN = "$CVMFSEXEC_DIR/.cvmfsexec/dist/cvmfs/singularity.galaxyproject.org/all/img"


def test_rewrite_container_applies_compute_environment_rewrite():
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == REWRITTEN


def test_rewrite_container_noop_without_matching_rule():
    # unstructured_path_rewrite returns None when no file_actions rule matches.
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_without_compute_environment():
    # No compute environment => not rewrite_parameters mode; leave image as-is.
    container = _container(IMAGE)
    PulsarJobRunner._rewrite_container_for_compute_environment(container, None)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_without_container():
    # Should not raise when there is no resolved container.
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(None, compute_environment)
