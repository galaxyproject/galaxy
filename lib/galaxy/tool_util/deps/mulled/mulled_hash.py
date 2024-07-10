#!/usr/bin/env python
"""Produce a mulled hash for specified conda targets.

Examples

Produce a mulled hash with:

    mulled-hash samtools=1.3.1,bedtools=2.22
"""

from ._cli import arg_parser
from .mulled_build import target_str_to_targets
from .util import (
    v1_image_name,
    v2_image_name,
)


def _mulled_hash(hash, targets):
    """
    >>> _mulled_hash(hash="v2", targets="samtools=1.3.1,bedtools=2.26.0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619'
    >>> _mulled_hash(hash="v2", targets="samtools=1.3.1=h9071d68_10,bedtools=2.26.0=0")
    'mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:8e86df67d257ce6494ae12b2c60e1b94025ea529'
    """
    targets = target_str_to_targets(targets)
    image_name = v2_image_name if hash == "v2" else v1_image_name
    return image_name(targets)


def main(argv=None):
    """
    Main entry-point for the CLI tool.
    """
    parser = arg_parser(argv, globals())
    parser.add_argument(
        "targets", metavar="TARGETS", default=None, help="Comma-separated packages for calculating the mulled hash."
    )
    parser.add_argument("--hash", dest="hash", choices=["v1", "v2"], default="v2")
    args = parser.parse_args()
    print(_mulled_hash(args.hash, args.targets))


__all__ = ("main",)

if __name__ == "__main__":
    main()
