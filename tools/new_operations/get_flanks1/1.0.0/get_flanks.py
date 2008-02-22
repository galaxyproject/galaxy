#! /usr/bin/python
#Done by: Guru

"""
Get Flanking regions.

usage: %prog input out_file size direction region
   -l, --cols=N,N,N,N: Columns for chrom, start, end, strand in file
   -o, --off=N: Offset
"""

import sys, sets, re, os
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main(): 
    try:
        if int( sys.argv[3] ) < 0:
            raise Exception
    except:
        stop_err( "Length of flanking region(s) must be a non-negative integer." )

    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols )
        inp_file, out_file, size, direction, region = args
        if strand_col_1 <= 0:
            strand = "+"        #if strand is not defined, default it to +
    except:
        stop_err( "Metadata issue, correct the metadata attributes by clicking on the pencil icon in the history item." )
    try:
        offset = int(options.off)
        size = int(size)
    except:    
        stop_err( "Invalid offset or length entered. Try again by entering valid integer values." )
    try:
        fi = open(inp_file,'r')
    except:
        stop_err( "Unable to open input file" )
    try:
        fo = open(out_file,'w')
    except:
        stop_err( "Unable to open output file" )
    
    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = None
    elems = []
    j=0
    for i, line in enumerate( fi ):
        line = line.strip()
        if line and (not line.startswith( '#' )) and line != '':
            j+=1
            try:
                elems = line.split('\t')
                #if the start and/or end columns are not numbers, skip that line.
                assert int(elems[start_col_1])
                assert int(elems[end_col_1])
                if strand_col_1 != -1:
                    strand = elems[strand_col_1]
                #if the stand value is not + or -, skip that line.
                assert strand in ['+', '-']
                if direction == 'Upstream':
                    if strand == '+':
                        if region == 'end':
                            elems[end_col_1] = str(int(elems[end_col_1]) + offset)
                            elems[start_col_1] = str( int(elems[end_col_1]) - size )
                        else:
                            elems[end_col_1] = str(int(elems[start_col_1]) + offset)
                            elems[start_col_1] = str( int(elems[end_col_1]) - size )
                    elif strand == '-':
                        if region == 'end':
                            elems[start_col_1] = str(int(elems[start_col_1]) - offset)
                            elems[end_col_1] = str(int(elems[start_col_1]) + size)
                        else:
                            elems[start_col_1] = str(int(elems[end_col_1]) - offset)
                            elems[end_col_1] = str(int(elems[start_col_1]) + size)
                    assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                    print >>fo, '\t'.join(elems)
                                
                elif direction == 'Downstream':
                    if strand == '-':
                        if region == 'start':
                           elems[end_col_1] = str(int(elems[end_col_1]) - offset)
                           elems[start_col_1] = str( int(elems[end_col_1]) - size )
                        else:
                           elems[end_col_1] = str(int(elems[start_col_1]) - offset)
                           elems[start_col_1] = str( int(elems[end_col_1]) - size )
                    elif strand == '+':
                        if region == 'start':
                            elems[start_col_1] = str(int(elems[start_col_1]) + offset)
                            elems[end_col_1] = str(int(elems[start_col_1]) + size)
                        else:
                            elems[start_col_1] = str(int(elems[end_col_1]) + offset)
                            elems[end_col_1] = str(int(elems[start_col_1]) + size)
                    assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                    print >>fo, '\t'.join(elems)
                    
                elif direction == 'Both':
                    if strand == '-':
                        if region == 'start':
                            start = str(int(elems[end_col_1]) - offset)
                            end1 = str(int(start) + size)
                            end2 = str(int(start) - size)
                            elems[start_col_1]=start
                            elems[end_col_1]=end1
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=end2
                            elems[end_col_1]=start
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                        elif region == 'end':
                            start = str(int(elems[start_col_1]) - offset)
                            end1 = str(int(start) + size)
                            end2 = str(int(start) - size)
                            elems[start_col_1]=start
                            elems[end_col_1]=end1
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=end2
                            elems[end_col_1]=start
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                        else:
                            start1 = str(int(elems[end_col_1]) - offset)
                            end1 = str(int(start1) + size)
                            start2 = str(int(elems[start_col_1]) - offset)
                            end2 = str(int(start2) - size)
                            elems[start_col_1]=start1
                            elems[end_col_1]=end1
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=end2
                            elems[end_col_1]=start2
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                    elif strand == '+':
                        if region == 'start':
                            start = str(int(elems[start_col_1]) + offset)
                            end1 = str(int(start) - size)
                            end2 = str(int(start) + size)
                            elems[start_col_1]=end1
                            elems[end_col_1]=start
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=start
                            elems[end_col_1]=end2
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                        elif region == 'end':
                            start = str(int(elems[end_col_1]) + offset)
                            end1 = str(int(start) - size)
                            end2 = str(int(start) + size)
                            elems[start_col_1]=end1
                            elems[end_col_1]=start
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=start
                            elems[end_col_1]=end2
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                        else:
                            start1 = str(int(elems[start_col_1]) + offset)
                            end1 = str(int(start1) - size)
                            start2 = str(int(elems[end_col_1]) + offset)
                            end2 = str(int(start2) + size)
                            elems[start_col_1]=end1
                            elems[end_col_1]=start1
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                            elems[start_col_1]=start2
                            elems[end_col_1]=end2
                            assert int(elems[start_col_1]) > 0 and int(elems[end_col_1]) > 0
                            print >>fo, '\t'.join(elems)
                
            except:
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
    fo.close()
    fi.close()
    
    #If number of skipped lines = num of lines in the file, inform the user to check metadata attributes of the input file.
    if skipped_lines == j:
        print 'Data issue: Skipped all lines in your input. Check the metadata attributes of the chosen input by clicking on the pencil icon next to it.'
        sys.exit()
    elif skipped_lines > 0:
        print '(Data issue: skipped %d invalid lines starting at line #%d which is "%s")' % ( skipped_lines, first_invalid_line, invalid_line )
    print 'Location : %s, Region : %s, Flank-length : %d, Offset : %d ' %(direction, region, size, offset)
    
if __name__ == "__main__":
    main()