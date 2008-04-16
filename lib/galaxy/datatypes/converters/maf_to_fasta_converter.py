#!/usr/bin/env python
#Dan Blankenberg

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
from galaxy.tools.util import maf_utilities

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    out = open( output_name, 'w' )
    count = 0
    for count, maf in enumerate( bx.align.maf.Reader( open( input_name, 'r' ) ) ):
        for c in maf.components:
            spec, chrom = bx.align.maf.src_split( c.src )
            if not spec or not chrom:
                    spec = chrom = c.src
            out.write( "%s\n" % maf_utilities.get_fasta_header( c, suffix = "%s_%i" % ( spec, count ) ) )
            out.write( "%s\n" % c.text )
        out.write( "\n" )
    out.close()
    print "%i MAF blocks converted to FASTA." % ( count )


if __name__ == "__main__": __main__()
