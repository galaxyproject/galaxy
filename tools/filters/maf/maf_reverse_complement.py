#!/usr/bin/env python2.4

"""
Reads a gene BED and an indexed MAF. Produces a FASTA file containing
the aligned gene sequences, based upon the provided coordinates

If index_file is not provided maf_file.index is used.

Alignment blocks are layered ontop of each other based upon score.

usage: %prog input_maf_file output_maf_file
"""
#Dan Blankenberg
#import psyco_full
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import sys


def __main__():

    #Parse Command Line
    input_file = sys.argv.pop(1)
    output_file = sys.argv.pop(1)
    
    try:
        maf_writer = bx.align.maf.Writer( open(output_file, 'w') )
    except:
        print sys.stderr, "Unable to open output file"
        sys.exit()
    try:
        count = 0
        for maf in bx.align.maf.Reader( open( input_file ) ):
            maf_writer.write(maf.reverse_complement())
            count += 1
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    print "%i regions were reverse complemented." % count
    maf_writer.close()
if __name__ == "__main__": __main__()
