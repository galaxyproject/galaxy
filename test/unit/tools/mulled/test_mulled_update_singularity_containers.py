import pytest

from galaxy.tools.deps.mulled.mulled_update_singularity_containers import docker_to_singularity
from galaxy.util import which


@pytest.mark.skipif(not which('singularity'), reason="requires singularity but singularity not on PATH")
def test_docker_to_singularity(tmp_path):
    tmp_dir = str(tmp_path)
    errors = docker_to_singularity('abundancebin:1.0.1--0', 'singularity', tmp_dir, no_sudo=True)
    assert errors is None
    assert tmp_path.joinpath('abundancebin:1.0.1--0').exists()
