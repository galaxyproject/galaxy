#! /usr/bin/python
#by: Guruprasad Ananda

"""
This tool finds the closest up- and/or down-stream feature in input2 for every interval in input1.

usage: %prog input1 input2 out_file direction
   -1, --cols1=N,N,N,N: Columns for chrom, start, end, strand in file1
   -2, --cols2=N,N,N,N: Columns for chrom, start, end, strand in file2
"""

import sys, os, tempfile, commands
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
from galaxy.tools.util.galaxyops import *

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main(): 
    infile1_includes_strand = False
    strand = "+"        #if strand is not defined, default it to +
    
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )
        infile1, infile2, out_file, direction = args
        if strand_col_1 >= 0:
            infile1_includes_strand = True      
    except:
        stop_err( "Metadata issue, correct the metadata attributes by clicking on the pencil icon in the history item." )

    try:
        fo = open(out_file,'w')
    except:
        stop_err( "Unable to open output file" )
    
    tmpfile1 = tempfile.NamedTemporaryFile()
    tmpfile2 = tempfile.NamedTemporaryFile()
    
    try:
        #Sort the features file based on decreasing end positions 
        command_line1 = "sort -f -n -r -k " + str( end_col_2 + 1 ) + " -o " + tmpfile1.name + " " + infile2
        #Sort the features file based on increasing start positions
        command_line2 = "sort -f -n -k " + str( start_col_2 + 1 ) + " -o " + tmpfile2.name + " " + infile2
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )
    
    error_code1, stdout = commands.getstatusoutput(command_line1)
    error_code2, stdout = commands.getstatusoutput(command_line2)
    
    if error_code1 != 0:
        stop_err( "Sorting input dataset resulted in error: %s: %s" %( error_code1, stdout ))
    if error_code2 != 0:
        stop_err( "Sorting input dataset resulted in error: %s: %s" %( error_code2, stdout ))

    if direction == 'Upstream' or direction == 'Both':
        if strand == '+':
            tmp_file_up = tmpfile1.name
        elif strand == '-':
            tmp_file_up = tmpfile2.name
    if direction == 'Downstream' or direction == 'Both':
        if strand == '-':
            tmp_file_down = tmpfile1.name
        elif strand == '+':
            tmp_file_down = tmpfile2.name

    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = None
    elems = []
    i = 0

    for i, line in enumerate( file( infile1 ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            try:
                elems = line.split( '\t' )
                chr = elems[chr_col_1]
                start = int( elems[start_col_1] )
                end = int( elems[end_col_1] )
                if infile1_includes_strand:
                    strand = elems[strand_col_1]
                    assert strand in ['+', '-']
            except:
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
                    continue

            if direction == 'Upstream' or direction == 'Both':
                for fline in file( tmp_file_up ):
                    fline = fline.rstrip( '\r\n' )
                    if fline and not fline.startswith( '#' ):
                        try:
                            felems = fline.split( '\t' )
                            if chr != felems[chr_col_2]:
                                continue
                            try:
                                fstrand = felems[strand_col_2]
                            except:
                                fstrand = ""
                            if fstrand and strand != fstrand:
                                continue
                            fstart = int( felems[start_col_2] )
                            fend = int( felems[end_col_2] )
                            if strand == '+' and fend < start:    
                                #Highest feature end value encountered i.e. the closest upstream feature found
                                fo.write( "%s\t%s\n" % ( line, fline ) )
                                break
                            elif strand == '-' and fstart > end:    
                                #Lowest feature start value encountered i.e. the closest upstream feature found
                                fo.write( "%s\t%s\n" % ( line, fline ) )
                                break
                        except:
                            continue
            if direction == 'Downstream' or direction == 'Both':
                for fline in file( tmp_file_down ):
                    fline = fline.rstrip( '\r\n' )
                    if fline and not fline.startswith( '#' ):
                        try:
                            felems = fline.split( '\t' )
                            if chr != felems[chr_col_2]:
                                continue
                            try:
                                fstrand = felems[strand_col_2]
                            except:
                                fstrand = ""
                            if fstrand and strand != fstrand:
                                continue
                            fstart = int( felems[start_col_2] )
                            fend = int( felems[end_col_2] )
                            if strand == '-' and fend < start:
                                #Highest feature end value encountered i.e. the closest DOWNstream feature found
                                fo.write( "%s\t%s\n" % ( line, fline ) )
                                break
                            elif strand == '+' and fstart > end:    
                                #Lowest feature start value encountered i.e. the closest DOWNstream feature found
                                fo.write( "%s\t%s\n"  % ( line, fline ) )
                                break
                        except:
                            continue
    fo.close()
    
    #If number of skipped lines = num of lines in the file, inform the user to check metadata attributes of the input file.
    if skipped_lines and skipped_lines == i:
        print 'All lines in input dataset invalid, check the metadata attributes by clicking on the pencil icon in the history item.'
        sys.exit()
    elif skipped_lines:
        print 'Data issue: skipped %d invalid lines starting at line #%d" "%s"' % ( skipped_lines, first_invalid_line, invalid_line )
    print 'Location: %s' % ( direction )
    
if __name__ == "__main__":
    main()