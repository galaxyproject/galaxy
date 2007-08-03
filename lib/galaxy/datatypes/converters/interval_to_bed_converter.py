#!/usr/bin/env python2.4
#Dan Blankenberg

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.intervals.io

def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    chromCol = int(sys.argv.pop(1))-1
    startCol = int(sys.argv.pop(1))-1
    endCol = int(sys.argv.pop(1))-1
    strandCol = int(sys.argv.pop(1))-1
    out = open(output_name,'w')
    count = 0
    for region in bx.intervals.io.NiceReaderWrapper( open(input_name, 'r' ), chrom_col=chromCol, start_col=startCol, end_col=endCol, strand_col=strandCol, fix_strand=True, return_header=False):
        out.write(region.chrom+"\t"+str(region.start)+"\t"+str(region.end)+"\tregion_"+str(count)+"\t"+"0\t"+region.strand+"\n")
        count += 1
    out.close()
    print "%i regions converted to BED." % (count)


if __name__ == "__main__": __main__()
