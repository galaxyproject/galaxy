"""Unit tests for Pulsar job runner utility methods."""

from types import SimpleNamespace

from galaxy.jobs.runners.pulsar import PulsarJobRunner


def _container(container_id, image_identifier_is_path=True):
    return SimpleNamespace(container_id=container_id, image_identifier_is_path=image_identifier_is_path)


class _ComputeEnvironment:
    """Minimal stand-in exposing only container_path_rewrite."""

    def __init__(self, rewrites):
        self._rewrites = rewrites

    def container_path_rewrite(self, path):
        return self._rewrites.get(path)


IMAGE = "/cvmfs/singularity.galaxyproject.org/all/img"
REWRITTEN = "/job/dir/.cvmfsexec/dist/cvmfs/singularity.galaxyproject.org/all/img"


def test_rewrite_container_applies_compute_environment_rewrite():
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == REWRITTEN


def test_rewrite_container_noop_without_matching_rule():
    # container_path_rewrite returns None when no file_actions rule matches.
    container = _container(IMAGE)
    compute_environment = _ComputeEnvironment({})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_when_identifier_not_a_path():
    # A registry/docker:// identifier is resolved by the compute node itself;
    # never route it through the path rewriter even if a rule would match.
    container = _container("docker://quay.io/biocontainers/bwa", image_identifier_is_path=False)
    compute_environment = _ComputeEnvironment({"docker://quay.io/biocontainers/bwa": REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(container, compute_environment)
    assert container.container_id == "docker://quay.io/biocontainers/bwa"


def test_rewrite_container_noop_without_compute_environment():
    # No compute environment => not rewrite_parameters mode; leave image as-is.
    container = _container(IMAGE)
    PulsarJobRunner._rewrite_container_for_compute_environment(container, None)
    assert container.container_id == IMAGE


def test_rewrite_container_noop_without_container():
    # Should not raise when there is no resolved container.
    compute_environment = _ComputeEnvironment({IMAGE: REWRITTEN})
    PulsarJobRunner._rewrite_container_for_compute_environment(None, compute_environment)
