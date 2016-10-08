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


import os
import time

from ._cli import arg_parser
from .mulled_build import (
    add_build_arguments,
    args_to_mull_targets_kwds,
    build_target,
    check_output,
    conda_versions,
    get_affected_packages,
    mull_targets,
)
from .util import quay_versions, version_sorted


def _fetch_repo_data(args):
    repo_data = args.repo_data
    channel = args.channel
    if repo_data is None:
        repo_data = "%s-repodata.json" % channel
    if not os.path.exists(repo_data):
        check_output("wget --quiet https://conda.anaconda.org/%s/linux-64/repodata.json.bz2 -O '%s.bz2' && bzip2 -d '%s.bz2'" % (channel, repo_data, repo_data))
    return repo_data


def _new_versions(quay, conda):
    """Calculate the versions that are in conda but not on quay.io."""
    sconda = set(conda)
    squay = set(quay) if quay else set()
    return sconda - squay  # sconda.symmetric_difference(squay)


def run_channel(args, build_last_n_versions=1):
    """Build list of involucro commands (as shell snippet) to run."""
    pkgs = get_affected_packages(args)
    for pkg_name, pkg_tests in pkgs:
        repo_data = _fetch_repo_data(args)
        c = conda_versions(pkg_name, repo_data)
        # only package the most recent N versions
        c = version_sorted(c)[:build_last_n_versions]

        if not args.force_rebuild:
            time.sleep(1)
            q = quay_versions(args.namespace, pkg_name)
            versions = _new_versions(q, c)
        else:
            versions = c

        for tag in versions:
            target = build_target(pkg_name, tag=tag)
            targets = [target]
            mull_targets(targets, test=pkg_tests, **args_to_mull_targets_kwds(args))


def get_pkg_names(args):
    """Print package names that would be affected."""
    print('\n'.join([pkg_name for pkg_name, pkg_tests in get_affected_packages(args)]))


def add_channel_arguments(parser):
    """Add arguments only used if running mulled over a whole conda channel."""
    parser.add_argument('--repo-data', dest='repo_data', default=None,
                        help='Published repository data (will be fetched from --channel if not available and written). Defaults to [channel_name]-repodata.json.')
    parser.add_argument('--diff-hours', dest='diff_hours', default="25",
                        help='If finding all recently changed recipes, use this number of hours.')
    parser.add_argument('--recipes-dir', dest="recipes_dir", default="./bioconda-recipes")


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_channel_arguments(parser)
    add_build_arguments(parser)
    parser.add_argument('command', metavar='COMMAND', help='Command (list, build-and-test, build, all)')
    parser.add_argument('--targets', dest="targets", default=None, help="Build a single container with specific package(s).")
    parser.add_argument('--repository-name', dest="repository_name", default=None, help="Name of a single container (leave blank to auto-generate based on packages).")
    args = parser.parse_args()
    if args.command == "list":
        get_pkg_names(args)
    else:
        run_channel(args)


__all__ = ["main"]


if __name__ == '__main__':
    main()
