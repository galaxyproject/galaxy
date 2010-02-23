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
    try:
        extension = sys.argv[8]
    except:
        extension = 'interval' #default extension
    
    skipped_lines = 0
    first_skipped_line = None
    out = open( output_name,'w' )
    count = 0
    #does file already conform to bed strict?
    #if so, we want to keep extended columns, otherwise we'll create a generic 6 column bed file
    strict_bed = True
    if extension in [ 'bed', 'bedstrict' ] and ( chromCol, startCol, endCol, nameCol, strandCol ) == ( 0, 1, 2, 3, 5 ):
        for count, line in enumerate( open( input_name ) ):
            line = line.strip()
            if line == "" or line.startswith("#"):
                skipped_lines += 1
                if first_skipped_line is None:
                    first_skipped_line = count + 1
                continue
            fields = line.split('\t')
            try:
                if len(fields) > 12:
                    strict_bed = False
                    break
                if len(fields) > 6:
                    int(fields[6])
                    if len(fields) > 7:
                        int(fields[7])
                        if len(fields) > 8:
                            if int(fields[8]) != 0:
                                strict_bed = False
                                break
                            if len(fields) > 9:
                                int(fields[9])
                                if len(fields) > 10:
                                    fields2 = fields[10].rstrip(",").split(",") #remove trailing comma and split on comma
                                    for field in fields2: 
                                        int(field)
                                    if len(fields) > 11:
                                        fields2 = fields[11].rstrip(",").split(",") #remove trailing comma and split on comma
                                        for field in fields2:
                                            int(field)
            except: 
                strict_bed = False
                break
            out.write( "%s\n" % line )
    else:
        strict_bed = False
    out.close()
    
    if not strict_bed:
        skipped_lines = 0
        first_skipped_line = None
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
                if first_skipped_line is None:
                    first_skipped_line = count + 1
        out.close()
    print "%i regions converted to BED." % ( count + 1 - skipped_lines )
    if skipped_lines > 0:
        print "Skipped %d blank or invalid lines starting with line # %d." % ( skipped_lines, first_skipped_line )

if __name__ == "__main__": __main__()
