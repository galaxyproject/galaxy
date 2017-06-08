"""Build all composite mulled recipes discovered in TSV files.

Use mulled-build-channel to build images for single recipes for a whole conda
channel. This script instead builds images for combinations of recipes. This
script can be given a single TSV file or a directory of TSV files to process.

Examples:

Build all recipes discovered in tsv files in a single directory.

    mulled-build-files build

"""

import collections
import glob
import os

from ._cli import arg_parser
from .mulled_build import (
    add_build_arguments,
    args_to_mull_targets_kwds,
    BuildExistsException,
    mull_targets,
    target_str_to_targets,
)


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_build_arguments(parser)
    parser.add_argument('command', metavar='COMMAND', help='Command (build-and-test, build, all)')
    parser.add_argument('files', metavar="FILES", default=".",
                        help="Path to directory (or single file) of TSV files describing composite recipes.")
    args = parser.parse_args()
    for (targets, image_build, name_override) in generate_targets(args.files):
        if not image_build and len(targets) > 1:
            # Specify an explict tag in this case.
            image_build = "0"
        try:
            mull_targets(
                targets,
                image_build=image_build,
                name_override=name_override,
                **args_to_mull_targets_kwds(args)
            )
        except BuildExistsException:
            continue


def generate_targets(target_source):
    """Generate all targets from TSV files in specified file or directory."""
    target_source = os.path.abspath(target_source)
    if os.path.isdir(target_source):
        target_source_files = glob.glob(target_source + "/*.tsv")
    else:
        target_source_files = [target_source]

    for target_source_file in target_source_files:
        with open(target_source_file, "r") as f:
            for line in f.readlines():
                if line:
                    line = line.strip()

                if not line or line.startswith("#"):
                    continue

                yield line_to_targets(line)


def line_to_targets(line_str):
    line = _parse_line(line_str)
    return (target_str_to_targets(line.targets), line.image_build, line.name_override)


_Line = collections.namedtuple("_Line", ["targets", "image_build", "name_override"])


def _parse_line(line_str):
    line_parts = line_str.split("\t")
    assert len(line_parts) < 3, "Too many fields in line [%s], expect at most 3 - targets, image build number, and name override." % line_str
    line_parts += [None] * (3 - len(line_parts))
    return _Line(*line_parts)


__all__ = ("main", )


if __name__ == '__main__':
    main()
