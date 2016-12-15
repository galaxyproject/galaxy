#!/usr/bin/env python
from __future__ import print_function

import sys

assert sys.version_info[:2] >= ( 2, 4 )


def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name, 'w' )
    i = 0
    for i, line in enumerate( open( input_name ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            try:
                elems = line.split( '\t' )
                start = str( int( elems[3] ) - 1 )
                strand = elems[6]
                if strand not in ['+', '-']:
                    strand = '+'
                # GFF format: chrom source, name, chromStart, chromEnd, score, strand
                # Bed format: chrom, chromStart, chromEnd, name, score, strand
                #
                # Replace any spaces in the name with underscores so UCSC will not complain
                name = elems[2].replace(" ", "_")
                out.write( "%s\t%s\t%s\t%s\t0\t%s\n" % ( elems[0], start, elems[4], name, strand ) )
            except:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
        else:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = i + 1
    out.close()
    info_msg = "%i lines converted to BED.  " % ( i + 1 - skipped_lines )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % ( skipped_lines, first_skipped_line )
    print(info_msg)


if __name__ == "__main__":
    __main__()
