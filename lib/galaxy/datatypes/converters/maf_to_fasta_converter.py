#!/usr/bin/env python
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities

assert sys.version_info[:2] >= ( 2, 4 )


def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    out = open( output_name, 'w' )
    count = 0
    for count, block in enumerate( bx.align.maf.Reader( open( input_name, 'r' ) ) ):
        spec_counts = {}
        for c in block.components:
            spec, chrom = maf_utilities.src_split( c.src )
            if spec not in spec_counts:
                spec_counts[ spec ] = 0
            else:
                spec_counts[ spec ] += 1
            out.write( "%s\n" % maf_utilities.get_fasta_header( c, { 'block_index' : count, 'species' : spec, 'sequence_index' : spec_counts[ spec ] }, suffix="%s_%i_%i" % ( spec, count, spec_counts[ spec ] ) ) )
            out.write( "%s\n" % c.text )
        out.write( "\n" )
    out.close()
    print("%i MAF blocks converted to FASTA." % ( count ))


if __name__ == "__main__":
    __main__()
