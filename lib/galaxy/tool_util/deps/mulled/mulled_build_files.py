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
import sys

from ._cli import arg_parser
from .mulled_build import (
    add_build_arguments,
    args_to_mull_targets_kwds,
    BuildExistsException,
    mull_targets,
    target_str_to_targets,
)
KNOWN_FIELDS = ["targets", "image_build", "name_override", "base_image"]
FALLBACK_LINE_TUPLE = collections.namedtuple("FALLBACK_LINE_TUPLE", "targets image_build name_override base_image")


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_build_arguments(parser)
    parser.add_argument('command', metavar='COMMAND', help='Command (build-and-test, build, all)')
    parser.add_argument('files', metavar="FILES", default=".",
                        help="Path to directory (or single file) of TSV files describing composite recipes.")
    args = parser.parse_args()
    for target in generate_targets(args.files):
        try:
            ret = mull_targets(
                target.targets,
                image_build=target.image_build,
                name_override=target.name_override,
                base_image=target.base_image,
                determine_base_image=False,
                **args_to_mull_targets_kwds(args)
            )
        except BuildExistsException:
            continue
        if ret > 0:
            sys.exit(ret)


def generate_targets(target_source):
    """Generate all targets from TSV files in specified file or directory."""
    target_source = os.path.abspath(target_source)
    if os.path.isdir(target_source):
        target_source_files = glob.glob(f"{target_source}/*.tsv")
    else:
        target_source_files = [target_source]

    for target_source_file in target_source_files:
        # If no headers are defined we use the 4 default fields in the order
        # that has been used in galaxy-tool-util / galaxy-lib < 20.01
        line_tuple = FALLBACK_LINE_TUPLE
        with open(target_source_file) as f:
            for line in f.readlines():
                if line:
                    line = line.strip()
                    if line.startswith('#'):
                        # headers can define a different column order
                        line_tuple = tuple_from_header(line)
                    else:
                        yield line_to_targets(line, line_tuple)


def tuple_from_header(header):
    fields = header[1:].split('\t')
    for field in fields:
        assert field in KNOWN_FIELDS, f"'{field}' is not one of {KNOWN_FIELDS}"
    # Make sure tuple contains all fields
    for field in KNOWN_FIELDS:
        if field not in fields:
            fields.append(field)
    return collections.namedtuple("_Line", f"{' '.join(fields)}")


def line_to_targets(line_str, line_tuple):
    """Parse a line so that some columns can remain unspecified."""
    line_parts = line_str.split("\t")
    n_fields = len(line_tuple._fields)
    targets_column = line_tuple._fields.index('targets')
    assert len(line_parts) <= n_fields, f"Too many fields in line [{line_str}], expect at most {n_fields} - targets, image build number, and name override."
    line_parts += [None] * (n_fields - len(line_parts))
    line_parts[targets_column] = target_str_to_targets(line_parts[targets_column])
    return line_tuple(*line_parts)


__all__ = ("main", )


if __name__ == '__main__':
    main()
