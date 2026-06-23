#!/usr/bin/env python
"""Build a mulled images for all recent conda recipe updates that don't have existing images.

Examples:

Build mulled images for recent bioconda changes with:

    mulled-build-channel build

Build, test, and publish images with the follow command:

    mulled-build-channel all

See recent changes that would be built with:

    mulled-build-channel list

"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Protocol

from galaxy.util import requests
from ._cli import arg_parser
from .mulled_build import (
    add_build_arguments,
    args_to_mull_targets_kwds,
    build_target,
    conda_versions,
    docker_platform_tag_suffix,
    docker_platform_to_conda_subdir,
    get_affected_packages,
    mull_targets,
)
from .util import (
    quay_versions,
    version_sorted,
)


class _FetchRepoDataArgs(Protocol):
    channel: str
    repo_data: str


class _ChannelPackagesArgs(Protocol):
    recipes_dir: str
    diff_hours: str


class _RunChannelArgs(_FetchRepoDataArgs, _ChannelPackagesArgs, Protocol):
    force_rebuild: bool
    namespace: str


def _fetch_repo_data(args: _FetchRepoDataArgs) -> str:
    repo_data = args.repo_data
    channel = args.channel
    if not os.path.exists(repo_data):
        platform_tag = docker_platform_to_conda_subdir(getattr(args, "target_platform", None))
        subprocess.check_call(
            [
                "wget",
                "--quiet",
                f"https://conda.anaconda.org/{channel}/{platform_tag}/repodata.json.bz2",
                "-O",
                f"{repo_data}.bz2",
            ]
        )
        subprocess.check_call(["bzip2", "-d", f"{repo_data}.bz2"])
    return repo_data


def _unpublished_versions(quay: list[str], conda: list[str], platform_suffix: str | None = None) -> list[str]:
    """Calculate the versions that are in conda but not on quay.io."""
    squay = set(quay) if quay else set()
    if platform_suffix is None:
        return [v for v in conda if v not in squay]
    suffix = f"-{platform_suffix}"
    # Unsuffixed legacy tags represent amd64 builds and must not suppress
    # publication of the requested non-amd64 variant.
    return [v for v in conda if f"{v}{suffix}" not in squay]


def run_channel(args: _RunChannelArgs, build_last_n_versions: int = 1) -> None:
    """Build list of involucro commands (as shell snippet) to run."""
    session = requests.Session()
    for pkg_name, pkg_tests in get_affected_packages(args):
        repo_data = _fetch_repo_data(args)
        c = conda_versions(pkg_name, repo_data)
        # only package the most recent N versions
        c = version_sorted(c)[:build_last_n_versions]

        if not args.force_rebuild:
            time.sleep(1)
            q = quay_versions(args.namespace, pkg_name, session)
            versions = _unpublished_versions(q, c, docker_platform_tag_suffix(getattr(args, "target_platform", None)))
        else:
            versions = c

        for tag in versions:
            target = build_target(pkg_name, tag=tag)
            targets = [target]
            mull_targets(targets, test=pkg_tests, **args_to_mull_targets_kwds(args))


def get_pkg_names(args: _ChannelPackagesArgs) -> None:
    """Print package names that would be affected."""
    print("\n".join(pkg_name for pkg_name, pkg_tests in get_affected_packages(args)))


def add_channel_arguments(parser):
    """Add arguments only used if running mulled over a whole conda channel."""
    parser.add_argument(
        "--channel",
        dest="channel",
        default="bioconda",
        help="Conda channel to fetch repodata from. Default: bioconda",
    )
    parser.add_argument(
        "--repo-data",
        dest="repo_data",
        required=True,
        help="Published repository data. Will be auto-downloaded from --channel if file does not exist.",
    )
    parser.add_argument(
        "--diff-hours",
        dest="diff_hours",
        default="25",
        help="If finding all recently changed recipes, use this number of hours.",
    )
    parser.add_argument("--recipes-dir", dest="recipes_dir", default="./bioconda-recipes")
    parser.add_argument(
        "--force-rebuild", dest="force_rebuild", action="store_true", help="Rebuild package even if already published."
    )


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_channel_arguments(parser)
    add_build_arguments(parser)
    parser.add_argument("command", metavar="COMMAND", help="Command (list, build-and-test, build, all)")
    parser.add_argument(
        "--targets", dest="targets", default=None, help="Build a single container with specific package(s)."
    )
    parser.add_argument(
        "--repository-name",
        dest="repository_name",
        default=None,
        help="Name of a single container (leave blank to auto-generate based on packages).",
    )
    args = parser.parse_args()
    if args.command == "list":
        get_pkg_names(args)
    else:
        run_channel(args)


__all__ = ("main",)


if __name__ == "__main__":
    main()
