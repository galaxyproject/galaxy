#!/usr/bin/env python
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities

assert sys.version_info[:2] >= (2, 6)


def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    species = sys.argv.pop(1)
    count = 0
    with open(output_name, 'w') as out:
        # write interval header line
        out.write("#chrom\tstart\tend\tstrand\n")
        try:
            with open(input_name, 'r') as fh:
                for block in bx.align.maf.Reader(fh):
                    for c in maf_utilities.iter_components_by_src_start(block, species):
                        if c is not None:
                            out.write("%s\t%i\t%i\t%s\n" % (maf_utilities.src_split(c.src)[-1], c.get_forward_strand_start(), c.get_forward_strand_end(), c.strand))
                            count += 1
        except Exception as e:
            print("There was a problem processing your input: %s" % e, file=sys.stderr)
    print("%i MAF blocks converted to Genomic Intervals for species %s." % (count, species))


if __name__ == "__main__":
    __main__()
