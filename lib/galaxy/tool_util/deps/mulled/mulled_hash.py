#!/usr/bin/env python
"""Produce a mulled hash for specified conda targets.

Galaxy does not use the "v1" hash format for uncontainerized conda dependencies. For the mulled hash for conda
dependencies, use `--hash conda`

Examples

Produce a mulled hash with:

    mulled-hash samtools=1.3.1,bedtools=2.22
"""

from typing import Literal

from ._cli import arg_parser
from ..conda_util import hash_conda_packages
from .mulled_build import target_str_to_targets
from .util import (
    v1_image_name,
    v2_image_name,
)


IMAGE_FUNCS = {
    "conda": lambda x: f"mulled-v1-{hash_conda_packages(x)}",
    "v1": v1_image_name,
    "v2": v2_image_name,
}


def _mulled_hash(hash: Literal["conda", "v1", "v2"], targets_str: str):
    """
    >>> _mulled_hash("v2", "samtools=1.3.1,bedtools=2.26.0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    >>> _mulled_hash("v2", "samtools=1.3.1=h9071d68_10,bedtools=2.26.0=0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    """
    targets = target_str_to_targets(targets_str)
    return IMAGE_FUNCS[hash](targets)


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    parser.add_argument(
        "targets", metavar="TARGETS", default=None, help="Comma-separated packages for calculating the mulled hash."
    )
    parser.add_argument("--hash", dest="hash", choices=IMAGE_FUNCS.keys(), default="v2")
    args = parser.parse_args()
    print(_mulled_hash(args.hash, args.targets))


__all__ = ("main",)

if __name__ == "__main__":
    main()
