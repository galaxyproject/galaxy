#!/usr/bin/env python
"""
Read a maf and split blocks by unique species combinations
"""
from __future__ import print_function

import sys

from bx.align import maf

from galaxy.tools.util import maf_utilities
from galaxy.util import string_as_bool


def __main__():
    try:
        maf_reader = maf.Reader(open(sys.argv[1]))
    except Exception as e:
        maf_utilities.tool_fail("Error opening MAF: %s" % e)
    try:
        out = maf.Writer(open(sys.argv[2], "w"))
    except Exception as e:
        maf_utilities.tool_fail("Error opening file for output: %s" % e)
    try:
        collapse_columns = string_as_bool(sys.argv[3])
    except Exception as e:
        maf_utilities.tool_fail("Error determining collapse columns value: %s" % e)

    start_count = 0
    end_count = 0
    for start_count, start_block in enumerate(maf_reader):  # noqa: B007
        for block in maf_utilities.iter_blocks_split_by_species(start_block):
            if collapse_columns:
                block.remove_all_gap_columns()
            out.write(block)
            end_count += 1
    out.close()

    if end_count:
        print("%i alignment blocks created from %i original blocks." % (end_count, start_count + 1))
    else:
        print("No alignment blocks were created.")


if __name__ == "__main__":
    __main__()
