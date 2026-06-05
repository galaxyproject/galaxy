from argparse import Namespace
from unittest import mock

from galaxy.tool_util.deps.mulled.mulled_build_channel import (
    _fetch_repo_data,
    _new_versions,
)


def test_fetch_repo_data_uses_target_platform(tmp_path):
    repo_data = tmp_path / "repodata.json"
    args = Namespace(channel="bioconda", repo_data=str(repo_data), target_platform="linux/arm64")
    with mock.patch("galaxy.tool_util.deps.mulled.mulled_build_channel.subprocess.check_call") as check_call:
        assert _fetch_repo_data(args) == str(repo_data)
    assert check_call.call_args_list[0] == mock.call(
        [
            "wget",
            "--quiet",
            "https://conda.anaconda.org/bioconda/linux-aarch64/repodata.json.bz2",
            "-O",
            f"{repo_data}.bz2",
        ]
    )


def test_fetch_repo_data_defaults_to_host_platform(tmp_path):
    repo_data = tmp_path / "repodata.json"
    args = Namespace(channel="bioconda", repo_data=str(repo_data))
    with (
        mock.patch("galaxy.tool_util.deps.mulled.mulled_build.conda_platform", return_value="osx-arm64"),
        mock.patch("galaxy.tool_util.deps.mulled.mulled_build_channel.subprocess.check_call") as check_call,
    ):
        assert _fetch_repo_data(args) == str(repo_data)
    assert check_call.call_args_list[0] == mock.call(
        [
            "wget",
            "--quiet",
            "https://conda.anaconda.org/bioconda/osx-arm64/repodata.json.bz2",
            "-O",
            f"{repo_data}.bz2",
        ]
    )


def test_new_versions_compares_platform_suffixed_quay_tags():
    assert _new_versions(["1.2--0-arm64"], ["1.2--0", "1.3--0"], "arm64") == ["1.3--0"]


def test_new_versions_ignores_legacy_unsuffixed_tags_for_non_amd64_builds():
    assert _new_versions(["1.2--0"], ["1.2--0"], "arm64") == ["1.2--0"]
