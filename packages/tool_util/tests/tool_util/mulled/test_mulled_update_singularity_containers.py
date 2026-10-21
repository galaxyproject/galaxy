import os

from galaxy.tool_util.deps.mulled.get_tests import main_test_search
from galaxy.tool_util.deps.mulled.mulled_update_singularity_containers import (
    docker_to_singularity,
    get_list_from_file,
    singularity_container_test,
)
from galaxy.util.unittest_utils import skip_unless_executable
from ..util import external_dependency_management


def test_get_list_from_file(tmp_path) -> None:
    list_file = os.path.join(tmp_path, "list_file.txt")
    with open(list_file, "w") as f:
        f.write("bbmap:36.84--0\nbiobambam:2.0.42--0\nconnor:0.5.1--py35_0\ndiamond:0.8.26--0\nedd:1.1.18--py27_0")
    assert get_list_from_file(list_file) == [
        "bbmap:36.84--0",
        "biobambam:2.0.42--0",
        "connor:0.5.1--py35_0",
        "diamond:0.8.26--0",
        "edd:1.1.18--py27_0",
    ]


@external_dependency_management
@skip_unless_executable("singularity")
def test_docker_to_singularity(tmp_path) -> None:
    docker_to_singularity("abundancebin:1.0.1--0", "singularity", tmp_path, no_sudo=True)
    assert tmp_path.joinpath("abundancebin:1.0.1--0").exists()


@external_dependency_management
@skip_unless_executable("singularity")
def test_singularity_container_test(tmp_path) -> None:
    containers = [
        "pybigwig:0.3.22--py36h54a71a5_0",  # test Python imports
        "samtools:1.0--1",
        "yasm:1.3.0--0",  # test missing tests
    ]
    tests = {container: main_test_search(container) for container in containers}
    for n in tests.keys():
        docker_to_singularity(n, "singularity", tmp_path, no_sudo=True)
    results = singularity_container_test(
        tests,
        "singularity",
        tmp_path,
    )
    assert "samtools:1.0--1" in results["passed"], results
    assert "pybigwig:0.3.22--py36h54a71a5_0" in results["passed"], results
    assert "yasm:1.3.0--0" in results["notest"], results
