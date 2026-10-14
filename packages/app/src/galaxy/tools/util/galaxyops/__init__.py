"""Utility functions for galaxyops"""

import sys

from galaxy.util import unicodify


def warn(msg):
    # TODO: since everything printed to stderr results in job.state = error, we
    # don't need both a warn and a fail...
    print(msg, file=sys.stderr)
    sys.exit(1)


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


# Default chrom, start, end, strand cols for a bed file
BED_DEFAULT_COLS = 0, 1, 2, 5


def parse_cols_arg(cols):
    """Parse a columns command line argument into a four-tuple"""
    if cols:
        # Handle case where no strand column included - in this case, cols
        # looks something like 1,2,3,
        if cols.endswith(","):
            cols += "0"
        col_list = [int(x) - 1 for x in cols.split(",")]
        return col_list
    else:
        return BED_DEFAULT_COLS


def default_printer(stream, exc, obj):
    print(f"{obj.linenum}: {obj.current_line}", file=stream)
    print(f"\tError: {unicodify(exc)}", file=stream)


def skipped(reader, filedesc=""):
    first_line, line_contents, problem = reader.skipped_lines[0]
    return f'Skipped {reader.skipped} invalid lines{filedesc}, 1st line #{first_line}: "{line_contents}", problem: {problem}'
