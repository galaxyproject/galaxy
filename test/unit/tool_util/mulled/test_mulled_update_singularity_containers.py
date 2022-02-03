import os
import shutil
import tempfile

import pytest

from galaxy.tool_util.deps.mulled.mulled_update_singularity_containers import (
    docker_to_singularity,
    get_list_from_file,
    singularity_container_test,
)
from galaxy.util import which
from ..util import external_dependency_management


def test_get_list_from_file():
    test_dir = tempfile.mkdtemp()
    try:
        list_file = os.path.join(test_dir, "list_file.txt")
        with open(list_file, "w") as f:
            f.write("bbmap:36.84--0\nbiobambam:2.0.42--0\nconnor:0.5.1--py35_0\ndiamond:0.8.26--0\nedd:1.1.18--py27_0")
        assert get_list_from_file(list_file) == [
            "bbmap:36.84--0",
            "biobambam:2.0.42--0",
            "connor:0.5.1--py35_0",
            "diamond:0.8.26--0",
            "edd:1.1.18--py27_0",
        ]
    finally:
        shutil.rmtree(test_dir)


@external_dependency_management
@pytest.mark.skipif(not which("singularity"), reason="requires singularity but singularity not on PATH")
def test_docker_to_singularity(tmp_path):
    tmp_dir = str(tmp_path)
    docker_to_singularity("abundancebin:1.0.1--0", "singularity", tmp_dir, no_sudo=True)
    assert tmp_path.joinpath("abundancebin:1.0.1--0").exists()


@external_dependency_management
@pytest.mark.skipif(not which("singularity"), reason="requires singularity but singularity not on PATH")
def test_singularity_container_test(tmp_path):
    test_dir = tempfile.mkdtemp()
    try:
        for n in ["pybigwig:0.1.11--py36_0", "samtools:1.0--1", "yasm:1.3.0--0"]:
            docker_to_singularity(n, "singularity", test_dir, no_sudo=True)
        results = singularity_container_test(
            {
                "pybigwig:0.1.11--py36_0": {
                    "imports": ["pyBigWig"],
                    "commands": [
                        'python -c "import pyBigWig; assert(pyBigWig.numpy == 1); assert(pyBigWig.remote == 1)"'
                    ],
                    "import_lang": "python -c",
                },
                "samtools:1.0--1": {
                    "commands": ["samtools --help"],
                    "import_lang": "python -c",
                    "container": "samtools:1.0--1",
                },
                "yasm:1.3.0--0": {},
            },
            "singularity",
            test_dir,
        )
        assert "samtools:1.0--1" in results["passed"]
        assert results["failed"][0]["imports"] == ["pyBigWig"]
        assert "yasm:1.3.0--0" in results["notest"]
    finally:
        shutil.rmtree(test_dir)
