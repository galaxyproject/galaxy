#!/usr/bin/env python
#Guruprasad Ananda
"""
Calculate coverage of one query on another, and append the coverage to
the last two columns as bases covered and percent coverage.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
"""

from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )

import sys, tempfile
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.merge import *
from bx.cookbook import doc_optparse

from galaxy.tools.util.galaxyops import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def main():

    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        in1_fname, in2_fname, out_fname = args
    except:
        stop_err( "Data issue: click the pencil icon in the history item to correct the metadata attributes." )
        
    try:
        out_file = open( out_fname, "w" )
    except:
        stop_err( "Unable to open output file." )
        
    chr_list = []
    start_list = []
    end_list = []
    skipped_lines_input2 = 0
    first_invalid_line_input2 = None
    invalid_line_input2 = ''
    for i, line in enumerate( open( in2_fname ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            try:
                chr_list.append( elems[chr_col_2] )
                start_list.append( elems[start_col_2] )
                end_list.append( elems[end_col_2] )
            except:
                skipped_lines_input2 += 1
                if first_invalid_line_input2 is None:
                    first_invalid_line_input2 = i + 1
                    invalid_line_input2 = line
    
    if not( chr_list ) and not( start_list ) and not( end_list ):
        stop_err( "Data issue: click the pencil icon in the history item to correct the metadata attributes." )

    skipped_lines_input1 = 0
    first_invalid_line_input1 = None
    invalid_line_input1 = ''
    for i, line in enumerate( open( in1_fname ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            fp = 0 #number of features fully present
            fp_p = 0 #% covered by fp features
            pp = 0 #number of overlapping features
            pp_p = 0 #% covered by pp features
            pp_l = 0 #partly present on left side of the window
            pp_l_p = 0 #% covered by pp_l features
            pp_r = 0 #partly present on right side of the window
            pp_r_p = 0 #% covered by pp_r features
            np = 0 #number of features present
            
            elems = line.split( '\t' )
            try:
                chr1 = elems[chr_col_1]
                start1 = int( elems[start_col_1] )
                end1 = int( elems[end_col_1] )
            except:
                chr1 = None
                skipped_lines_input1 += 1
                if first_invalid_line_input1 is None:
                    first_invalid_line_input1 = i + 1
                    invalid_line_input1 = line

            if not( chr1 in chr_list ):
                continue
            
            tmpfile1 = tempfile.NamedTemporaryFile( 'wb+' )
            
            for j, chr2 in enumerate( chr_list ):
                try:
                    start2 = int( start_list[j] )
                    end2 = int( end_list[j] )
                except:
                    # Not easy to deal with skipped lines here...
                    continue
                if chr2 == chr1:
                    if ( start2 < start1 and end2 < start1 ) or ( start2 > end1 and end2 > end1 ):
                        continue
                    if start2 in range( start1, end1 ) and end2 in range( start1, end1+1 ):    #feature completely lies in the window
                        fp += 1
                        tmpfile1.write( "%s\t%s\t%s\n" % ( chr2, str( start2 ), str( end2 ) ) )
                    elif ( start2 not in range( start1, end1 ) ) and ( end2 not in range( start1, end1 ) ):    #feature is longer than the window and covers the window completely                        #feature overlaps  the right side of the window
                        if ( start1 in range( start2, end2 ) ) and ( end1 in range( start2, end2 ) ):
                            fp += 1
                            fp_p += 100.00
                    elif ( start2 not in range( start1, end1 ) ) or ( end2 not in range( start1, end1 ) ):    #feature partially overlaps with the window
                        pp += 1
                        tmpfile1.write( "%s\t%s\t%s\n" % ( chr2, str( start2 ), str( end2 ) ) )

            tmpfile1.seek( 0 )
            g1 = NiceReaderWrapper( tmpfile1, chrom_col=chr_col_2, start_col=start_col_2, end_col=end_col_2, strand_col=strand_col_2, fix_strand=True )

            mincols = 1
            #merge over-lapping features before computing their coverage
            for merge_line in merge( g1, mincols=mincols ):
                if type( merge_line ) is GenomicInterval:
                    start = int( merge_line.startCol )
                    end = int( merge_line.endCol )
                elif type( merge_line ) is list:
                    start = int( merge_line[start_col_1] )
                    end = int( merge_line[end_col_1] )
                if start in range( start1, end1 ) and end in range( start1, end1 ):
                    fp_p += ( 100.0 * abs( end - start ) / abs( end1 - start1 ) )
                elif start in range( start1, end1 ) and end not in range( start1, end1 ):
                    fp_p += ( 100.0 * abs( end1 - start ) / abs( end1 - start1 ) )
                elif start not in range( start1, end1 ) and end in range( start1, end1 ):
                    fp_p += ( 100.0*abs( end - start1 ) / abs( end1 - start1 ) )

            if fp_p > 100:
                fp_p = 100.00
            out_file.write( "%s\t%d\t%d\t%2.2f\n" % ( line, fp, pp, fp_p ) )
    out_file.close()

    if skipped_lines_input1:
        print "Skipped %d invalid lines in 1st input starting at line # %d: '%s' " % ( skipped_lines_input1, first_invalid_line_input1, invalid_line_input1 )
    if skipped_lines_input2:
        print "Skipped %d invalid lines in 2nd input starting at line # %d: '%s'" % ( skipped_lines_input2, first_invalid_line_input2, invalid_line_input2 )

if __name__ == "__main__":
    main()
