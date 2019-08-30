#!/usr/bin/env python
"""
Read a maf and output a multiple block fasta file.
"""
# Dan Blankenberg
from __future__ import print_function

import sys
from collections import OrderedDict

from bx.align import maf

from galaxy.tools.util import maf_utilities


def __main__():
    try:
        maf_reader = maf.Reader(open(sys.argv[1]))
    except Exception as e:
        maf_utilities.tool_fail("Error opening input MAF: %s" % e)
    try:
        file_out = open(sys.argv[2], 'w')
    except Exception as e:
        maf_utilities.tool_fail("Error opening file for output: %s" % e)
    try:
        species = maf_utilities.parse_species_option(sys.argv[3])
        if species:
            num_species = len(species)
        else:
            num_species = 0
    except Exception as e:
        maf_utilities.tool_fail("Error determining species value: %s" % e)
    try:
        partial = sys.argv[4]
    except Exception as e:
        maf_utilities.tool_fail("Error determining keep partial value: %s" % e)

    if species:
        print("Restricted to species: %s" % ', '.join(species))
    else:
        print("Not restricted to species.")

    for block_num, block in enumerate(maf_reader):
        if species:
            block = block.limit_to_species(species)
            if len(maf_utilities.get_species_in_block(block)) < num_species and partial == "partial_disallowed":
                continue
        spec_counts = {}
        for component in block.components:
            spec, chrom = maf_utilities.src_split(component.src)
            if spec not in spec_counts:
                spec_counts[spec] = 0
            else:
                spec_counts[spec] += 1
            d = OrderedDict([('block_index', block_num), ('species', spec), ('sequence_index', spec_counts[spec])])
            file_out.write("%s\n" % maf_utilities.get_fasta_header(component, d, suffix="%s_%i_%i" % (spec, block_num, spec_counts[spec])))
            file_out.write("%s\n" % component.text)
        file_out.write("\n")
    file_out.close()


if __name__ == "__main__":
    __main__()
