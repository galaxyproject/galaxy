import os.path

import pytest

from galaxy.tool_util.deps.mulled.mulled_build import (
    base_image_for_targets,
    build_target,
    DEFAULT_BASE_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
    InvolucroContext,
    mull_targets,
    target_str_to_targets,
)
from galaxy.tool_util.deps.mulled.util import CondaInDockerContext
from ..util import external_dependency_management


@pytest.mark.parametrize(
    "target,version,base_image",
    [
        ("maker", None, DEFAULT_EXTENDED_BASE_IMAGE),
        ("qiime", "1.9.1", DEFAULT_EXTENDED_BASE_IMAGE),
        ("samtools", None, DEFAULT_BASE_IMAGE),
    ],
)
@external_dependency_management
def test_base_image_for_targets(target, version, base_image):
    target = build_target(target, version=version)
    conda_context = CondaInDockerContext()
    assert base_image_for_targets([target], conda_context) == base_image


@pytest.mark.parametrize("use_mamba", [False, True])
@external_dependency_management
def test_mulled_build_files_cli(use_mamba: bool, tmpdir) -> None:
    singularity_image_dir = tmpdir.mkdir("singularity image dir")
    target = build_target("zlib", version="1.2.13", build="h166bdaf_4")
    involucro_context = InvolucroContext(involucro_bin=os.path.join(tmpdir, "involucro"))
    exit_code = mull_targets(
        [target],
        involucro_context=involucro_context,
        command="build-and-test",
        singularity=True,
        use_mamba=use_mamba,
        singularity_image_dir=singularity_image_dir,
    )
    assert exit_code == 0
    assert singularity_image_dir.join("zlib:1.2.13--h166bdaf_4").exists()


def test_target_str_to_targets():
    target_str = "samtools=1.3.1--4,bedtools=2.22"
    targets = target_str_to_targets(target_str)
    assert (targets[0].package, targets[0].version, targets[0].build) == ("samtools", "1.3.1", "4")
    assert (targets[1].package, targets[1].version, targets[1].build) == ("bedtools", "2.22", None)
