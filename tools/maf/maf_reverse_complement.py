#!/usr/bin/env python
"""
Reads a MAF file. Produces a MAF file containing
the reverse complement for each block in the source file.

usage: %prog input_maf_file output_maf_file
"""
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.align.maf

from galaxy.tools.util import maf_utilities


def __main__():
    # Parse Command Line
    input_file = sys.argv.pop( 1 )
    output_file = sys.argv.pop( 1 )
    species = maf_utilities.parse_species_option( sys.argv.pop( 1 ) )

    try:
        maf_writer = bx.align.maf.Writer( open( output_file, 'w' ) )
    except:
        print(sys.stderr, "Unable to open output file")
        sys.exit()
    try:
        count = 0
        for count, maf in enumerate( bx.align.maf.Reader( open( input_file ) ) ):
            maf = maf.reverse_complement()
            if species:
                maf = maf.limit_to_species( species )
            maf_writer.write( maf )
    except:
        print("Your MAF file appears to be malformed.", file=sys.stderr)
        sys.exit()
    print("%i regions were reverse complemented." % count)
    maf_writer.close()


if __name__ == "__main__":
    __main__()
