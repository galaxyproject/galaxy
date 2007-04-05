#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Removes blocks that fall outside of specified size range.
"""

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

def __main__():

    input_maf_filename = sys.argv[1].strip()
    output_filename1 = sys.argv[2].strip()
    min_size = int(sys.argv[3].strip())
    max_size = int(sys.argv[4].strip())
    if max_size < 1: max_size = sys.maxint
    maf_writer = bx.align.maf.Writer( open(output_filename1, 'w') )
    maf_reader = bx.align.maf.Reader( open(input_maf_filename, 'r') )
    maf_count = 0
    for m in maf_reader:
        if min_size <= m.components[0].size <= max_size:
            maf_writer.write(m)
            maf_count += 1
    print "%i MAF blocks kept." % maf_count

if __name__ == "__main__": __main__()
