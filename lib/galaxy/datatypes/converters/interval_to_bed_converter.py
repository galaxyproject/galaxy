#!/usr/bin/env python
#Dan Blankenberg

import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.intervals.io

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    output_name = sys.argv[1]
    input_name = sys.argv[2]
    try:
        chromCol = int( sys.argv[3] ) - 1
    except:
        stop_err( "'%s' is an invalid chrom column, correct the column settings before attempting to convert the data format." % str( sys.argv[3] ) )
    try:
        startCol = int( sys.argv[4] ) - 1
    except:
        stop_err( "'%s' is an invalid start column, correct the column settings before attempting to convert the data format." % str( sys.argv[4] ) )
    try:
        endCol = int( sys.argv[5] ) - 1
    except:
        stop_err( "'%s' is an invalid end column, correct the column settings before attempting to convert the data format." % str( sys.argv[5] ) )
    try:
        strandCol = int( sys.argv[6] ) - 1
    except:
        strandCol = -1
    try:
        nameCol = int( sys.argv[7] ) - 1
    except:
        nameCol = -1
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name,'w' )
    count = 0
    for count, region in enumerate( bx.intervals.io.NiceReaderWrapper( open( input_name, 'r' ), chrom_col=chromCol, start_col=startCol, end_col=endCol, strand_col=strandCol, fix_strand=True, return_header=False, return_comments=False ) ):
        try:
            if nameCol >= 0:
                name = region.fields[nameCol]
            else:
                raise IndexError
        except:
            name = "region_%i" % count
        try:
            
            out.write( "%s\t%i\t%i\t%s\t%i\t%s\n" %  ( region.chrom, region.start, region.end, name, 0, region.strand ) )
        except:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = count + 1
    out.close()
    print "%i regions converted to BED." % ( count + 1 - skipped_lines )
    if skipped_lines > 0:
        print "Skipped %d blank or invalid lines starting with line # %d." % ( skipped_lines, first_skipped_line )

if __name__ == "__main__": __main__()
