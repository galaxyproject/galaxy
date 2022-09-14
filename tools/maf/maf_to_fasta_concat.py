#!/usr/bin/env python
"""
Read a maf and output a single block fasta file, concatenating blocks

usage %prog species1,species2 maf_file out_file
"""
# Dan Blankenberg
from __future__ import print_function

import sys

from bx.align import maf

from galaxy.tools.util import maf_utilities


def __main__():
    try:
        species = maf_utilities.parse_species_option(sys.argv[1])
    except Exception as e:
        maf_utilities.tool_fail("Error determining species value: %s" % e)
    try:
        input_filename = sys.argv[2]
    except Exception as e:
        maf_utilities.tool_fail("Error reading MAF filename: %s" % e)
    try:
        file_out = open(sys.argv[3], "w")
    except Exception as e:
        maf_utilities.tool_fail("Error opening file for output: %s" % e)

    if species:
        print("Restricted to species: %s" % ", ".join(species))
    else:
        print("Not restricted to species.")

    if not species:
        try:
            species = maf_utilities.get_species_in_maf(input_filename)
        except Exception as e:
            maf_utilities.tool_fail("Error determining species in input MAF: %s" % e)

    for spec in species:
        file_out.write(">" + spec + "\n")
        try:
            for start_block in maf.Reader(open(input_filename)):
                for block in maf_utilities.iter_blocks_split_by_species(start_block):
                    block.remove_all_gap_columns()  # remove extra gaps
                    component = block.get_component_by_src_start(
                        spec
                    )  # blocks only have one occurrence of a particular species, so this is safe
                    if component:
                        file_out.write(component.text)
                    else:
                        file_out.write("-" * block.text_size)
        except Exception as e:
            maf_utilities.tool_fail("Your MAF file appears to be malformed: %s" % e)
        file_out.write("\n")
    file_out.close()


if __name__ == "__main__":
    __main__()
