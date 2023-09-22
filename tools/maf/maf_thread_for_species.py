#!/usr/bin/env python
"""
Read a maf file and write out a new maf with only blocks having all of
the passed in species, after dropping any other species and removing columns
containing only gaps. This will attempt to fuse together any blocks
which are adjacent after the unwanted species have been dropped.

usage: %prog input_maf output_maf species1,species2
"""
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.align.maf
from bx.align.tools.fuse import FusingAlignmentWriter
from bx.align.tools.thread import (
    get_components_for_species,
    remove_all_gap_columns,
)


def main():
    input_file = sys.argv.pop(1)
    output_file = sys.argv.pop(1)
    species = sys.argv.pop(1).split(",")

    try:
        maf_reader = bx.align.maf.Reader(open(input_file))
    except Exception:
        print("Unable to open source MAF file", file=sys.stderr)
        sys.exit()
    try:
        maf_writer = FusingAlignmentWriter(bx.align.maf.Writer(open(output_file, "w")))
    except Exception:
        print("Unable to open output file", file=sys.stderr)
        sys.exit()
    try:
        for m in maf_reader:
            new_components = m.components
            if species != ["None"]:
                new_components = get_components_for_species(m, species)
            if new_components:
                remove_all_gap_columns(new_components)
                m.components = new_components
                m.score = 0.0
                maf_writer.write(m)
    except Exception as e:
        print("Error steping through MAF File: %s" % e, file=sys.stderr)
        sys.exit()
    maf_reader.close()
    maf_writer.close()

    print("Restricted to species: %s." % ", ".join(species))


if __name__ == "__main__":
    main()
