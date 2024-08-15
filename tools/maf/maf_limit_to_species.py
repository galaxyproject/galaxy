#!/usr/bin/env python
"""
Read a maf file and write out a new maf with only blocks having the
required species, after dropping any other species and removing
columns containing only gaps.

usage: %prog species,species2,... input_maf output_maf allow_partial min_species_per_block
"""
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities


def main():
    species = maf_utilities.parse_species_option(sys.argv[1])
    if species:
        spec_len = len(species)
    else:
        spec_len = 0
    try:
        maf_reader = bx.align.maf.Reader(open(sys.argv[2]))
        maf_writer = bx.align.maf.Writer(open(sys.argv[3], "w"))
    except Exception:
        print("Your MAF file appears to be malformed.", file=sys.stderr)
        sys.exit()
    allow_partial = False
    if int(sys.argv[4]):
        allow_partial = True
    min_species_per_block = int(sys.argv[5])

    maf_blocks_kept = 0
    for m in maf_reader:
        if species:
            m = m.limit_to_species(species)
        m.remove_all_gap_columns()
        spec_in_block_len = len(maf_utilities.get_species_in_block(m))
        if (
            not species or allow_partial or spec_in_block_len == spec_len
        ) and spec_in_block_len > min_species_per_block:
            maf_writer.write(m)
            maf_blocks_kept += 1

    maf_reader.close()
    maf_writer.close()

    if species:
        print("Restricted to species: %s." % ", ".join(species))
    print("%i MAF blocks have been kept." % maf_blocks_kept)


if __name__ == "__main__":
    main()
