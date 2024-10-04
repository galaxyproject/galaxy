#!/usr/bin/env python
"""Produce a mulled hash for specified conda targets.

Galaxy does not use the "v1" hash format for uncontainerized conda dependencies. For the mulled hash for conda
dependencies, use `--hash conda`

Examples

Produce a mulled hash with:

    mulled-hash samtools=1.3.1,bedtools=2.22
"""

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


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    parser.add_argument(
        "targets", metavar="TARGETS", default=None, help="Comma-separated packages for calculating the mulled hash."
    )
    parser.add_argument("--hash", dest="hash", choices=["conda", "v1", "v2"], default="v2")
    args = parser.parse_args()
    targets = target_str_to_targets(args.targets)
    image_name = IMAGE_FUNCS[args.hash]
    print(image_name(targets))


__all__ = ("main",)

if __name__ == "__main__":
    main()
