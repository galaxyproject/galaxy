#!/usr/bin/env python2.4
#Dan Blankenberg

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    species = sys.argv.pop(1)
    out = open(output_name,'w')
    count = 0
    #write interval header line
    out.write( "#chrom\tstart\tend\tstrand\n" )
    for maf in bx.align.maf.Reader( open(input_name, 'r') ):
        c = maf.get_component_by_src_start(species)
        if c is not None:
            out.write( "%s\t%i\t%i\t%s\n" % (bx.align.src_split(c.src)[-1], c.start, c.end, c.strand) )
            count += 1
    out.close()
    print "%i MAF blocks converted to Genomic Intervals for species %s." % (count, species)


if __name__ == "__main__": __main__()
