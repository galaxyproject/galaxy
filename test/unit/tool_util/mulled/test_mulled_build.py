import os.path
from argparse import (
    ArgumentParser,
    Namespace,
)
from unittest import mock

import pytest

from galaxy.tool_util.deps.mulled.mulled_build import (
    add_build_arguments,
    apply_platform_tag_suffix,
    args_to_mull_targets_kwds,
    base_image_for_targets,
    build_target,
    conda_platform,
    DEFAULT_BASE_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
    docker_platform_to_conda_subdir,
    get_conda_hits_for_targets,
    InvolucroContext,
    mull_targets,
    target_str_to_targets,
)
from galaxy.tool_util.deps.mulled.util import CondaInDockerContext
from ..util import external_dependency_management


@pytest.mark.parametrize(
    "target,version,base_image",
    [
        ("mzmine", None, DEFAULT_EXTENDED_BASE_IMAGE),
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
        determine_base_image=False,
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


@mock.patch("galaxy.tool_util.deps.mulled.mulled_build._platform_module.machine")
def test_conda_platform_fallback_to_linux64(mock_machine):
    mock_machine.return_value = "riscv64"
    with mock.patch("galaxy.tool_util.deps.mulled.mulled_build.IS_OS_X", False):
        assert conda_platform() == "linux-64"


@pytest.mark.parametrize(
    "target_platform,conda_subdir",
    [
        ("linux/amd64", "linux-64"),
        ("linux/arm64", "linux-aarch64"),
        ("linux/arm/v7", "linux-armv7l"),
        ("linux/ppc64le", "linux-ppc64le"),
    ],
)
def test_docker_platform_to_conda_subdir(target_platform, conda_subdir):
    assert docker_platform_to_conda_subdir(target_platform) == conda_subdir


def test_docker_platform_to_conda_subdir_defaults_to_host_platform():
    with mock.patch("galaxy.tool_util.deps.mulled.mulled_build.conda_platform", return_value="osx-arm64"):
        assert docker_platform_to_conda_subdir(None) == "osx-arm64"


def test_docker_platform_to_conda_subdir_rejects_unsupported_platform():
    with pytest.raises(ValueError, match="Unsupported target platform 'linux/riscv64'"):
        docker_platform_to_conda_subdir("linux/riscv64")


def test_target_platform_cli_argument_rejects_unsupported_platform():
    parser = ArgumentParser()
    add_build_arguments(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--target-platform", "linux/riscv64"])


@pytest.mark.parametrize(
    "image,expected",
    [
        ("samtools:1.3--0", "samtools:1.3--0-arm64"),
        ("mulled-v2-xxx:hash", "mulled-v2-xxx:hash-arm64"),
        ("some-image", "some-image:latest-arm64"),
        ("registry.example:5000/namespace/some-image", "registry.example:5000/namespace/some-image:latest-arm64"),
    ],
)
def test_apply_platform_tag_suffix(image, expected):
    assert apply_platform_tag_suffix(image, "linux/arm64") == expected


def test_apply_platform_tag_suffix_keeps_default_platform_tag():
    assert apply_platform_tag_suffix("samtools:1.3--0", "linux/amd64") == "samtools:1.3--0"


@mock.patch("galaxy.tool_util.deps.mulled.mulled_build._platform_module.machine", return_value="aarch64")
def test_apply_platform_tag_suffix_uses_native_non_amd64_platform(_mock_machine):
    assert apply_platform_tag_suffix("samtools:1.3--0", None) == "samtools:1.3--0-arm64"


def test_get_conda_hits_for_targets_uses_explicit_conda_platform():
    target = build_target("samtools")
    conda_context = mock.Mock()
    with mock.patch(
        "galaxy.tool_util.deps.mulled.mulled_build.best_search_result", return_value=({"name": "samtools"}, True)
    ) as best_search_result:
        assert get_conda_hits_for_targets([target], conda_context, "linux-aarch64") == [{"name": "samtools"}]
    best_search_result.assert_called_once_with(target, conda_context, platform="linux-aarch64")


def test_mull_targets_dry_run_uses_target_platform(capsys):
    target = build_target("samtools", version="1.3", build="0")
    assert mull_targets([target], target_platform="linux/arm64", determine_base_image=False, dry_run=True) == 0
    output = capsys.readouterr().out
    assert "--platform linux/arm64" in output
    assert "REPO=quay.io/biocontainers/samtools:1.3--0-arm64" in output


def test_mull_targets_rejects_target_platform_with_singularity():
    with pytest.raises(ValueError, match="--target-platform cannot be used with --singularity"):
        mull_targets([build_target("samtools")], target_platform="linux/arm64", singularity=True, dry_run=True)


def test_args_to_mull_targets_kwds_passes_target_platform():
    args = Namespace(
        involucro_path="custom-involucro",
        strict_channel_priority=True,
        target_platform="linux/arm64",
        verbose=False,
    )
    kwds = args_to_mull_targets_kwds(args)
    assert kwds["target_platform"] == "linux/arm64"
