#!/usr/bin/env python
"""Produce a mulled hash for specified conda targets.

Use ``--hash conda`` to calculate the hash used for Galaxy's uncontainerized
Conda environments. Despite sharing the ``mulled-v1`` prefix, that hash differs
from the version 1 container hash.

Examples

Produce a mulled hash with:

    mulled-hash samtools=1.3.1,bedtools=2.22
"""

from typing import Literal

from ._cli import arg_parser
from .mulled_build import target_str_to_targets
from .util import (
    v1_image_name,
    v2_image_name,
)
from ..conda_util import hash_conda_packages

HashType = Literal["conda", "v1", "v2"]
HASH_TYPES: tuple[HashType, ...] = ("conda", "v1", "v2")


def _mulled_hash(hash_type: HashType, targets_str: str) -> str:
    """
    >>> _mulled_hash("conda", "bedtools=2.30.0,samtools=1.9")
    'mulled-v1-ca195b12c14e35565e393a2d07f2deac7610d8126cc3460d217504efd11d4347'
    >>> _mulled_hash("v2", "samtools=1.3.1,bedtools=2.26.0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    >>> _mulled_hash("v2", "samtools=1.3.1=h9071d68_10,bedtools=2.26.0=0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    """
    targets = target_str_to_targets(targets_str)
    if hash_type == "conda":
        return f"mulled-v1-{hash_conda_packages(targets)}"
    if hash_type == "v1":
        return v1_image_name(targets)
    return v2_image_name(targets)


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    parser.add_argument(
        "targets", metavar="TARGETS", default=None, help="Comma-separated packages for calculating the mulled hash."
    )
    parser.add_argument("--hash", dest="hash", choices=HASH_TYPES, default="v2")
    args = parser.parse_args(argv)
    print(_mulled_hash(args.hash, args.targets))


__all__ = ("main",)

if __name__ == "__main__":
    main()
