import shutil
import tempfile

from galaxy.tool_util.deps.mulled.mulled_list import (
    get_missing_containers,
    get_missing_envs,
    get_singularity_containers,
)
from ..util import external_dependency_management

# def test_get_quay_containers():
#     lst = get_quay_containers()
#     assert 'samtools:1.0--1' in lst
#     assert 'abricate:0.4--pl5.22.0_0' in lst
#     assert 'samtools' not in lst


@external_dependency_management
def test_get_singularity_containers():
    lst = get_singularity_containers()
    assert "aragorn:1.2.36--1" in lst
    assert "znc:latest" not in lst


def test_get_missing_containers():
    test_dir = tempfile.mkdtemp()
    try:
        exclude_list = "%s/blocklist.txt" % test_dir
        with open(exclude_list, "w") as f:
            f.write("a\n\nb\nc\nd")
        containers = get_missing_containers(
            quay_list=["1", "2", "3", "a", "b", "z"], singularity_list=["3", "4", "5"], blocklist_file=exclude_list
        )
        assert containers == ["1", "2", "z"]
    finally:
        shutil.rmtree(test_dir)


def test_get_missing_envs():
    test_dir = tempfile.mkdtemp()
    try:
        exclude_list = "%s/blocklist.txt" % test_dir
        with open(exclude_list, "w") as f:
            f.write("a\n\nb\nc\nd")
        envs = get_missing_envs(
            quay_list=["1", "2", "3", "a", "b--2", "z--1"], conda_list=["3", "4", "5"], blocklist_file=exclude_list
        )
        assert envs == ["1", "2", "z--1"]
    finally:
        shutil.rmtree(test_dir)
