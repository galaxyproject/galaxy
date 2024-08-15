#!/usr/bin/env python
# Dan Blankenberg
"""
Reads a list of block numbers and a maf. Produces a new maf containing the
blocks specified by number.
"""
from __future__ import print_function

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities


def __main__():
    input_block_filename = sys.argv[1].strip()
    input_maf_filename = sys.argv[2].strip()
    output_filename1 = sys.argv[3].strip()
    block_col = int(sys.argv[4].strip()) - 1
    if block_col < 0:
        print("Invalid column specified", file=sys.stderr)
        sys.exit(0)
    species = maf_utilities.parse_species_option(sys.argv[5].strip())

    maf_writer = bx.align.maf.Writer(open(output_filename1, "w"))
    # we want to maintain order of block file and write blocks as many times as they are listed
    failed_lines = []
    for ctr, line in enumerate(open(input_block_filename)):
        try:
            block_wanted = int(line.split("\t")[block_col].strip())
        except Exception:
            failed_lines.append(str(ctr))
            continue
        try:
            for count, block in enumerate(bx.align.maf.Reader(open(input_maf_filename))):
                if count == block_wanted:
                    if species:
                        block = block.limit_to_species(species)
                    maf_writer.write(block)
                    break
        except Exception:
            print("Your MAF file appears to be malformed.", file=sys.stderr)
            sys.exit()
    if len(failed_lines) > 0:
        print("Failed to extract from %i lines (%s)." % (len(failed_lines), ",".join(failed_lines)))


if __name__ == "__main__":
    __main__()
