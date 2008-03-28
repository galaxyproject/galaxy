#!/usr/bin/env python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""
import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    infile = sys.argv[1]
    title_col = sys.argv[2]
    seq_col = sys.argv[3]
    outfile = sys.argv[4]        

    if title_col == None or title_col == 'None' or seq_col == None or seq_col == 'None':
        stop_err( "Columns not specified." )
    try:
        seq_col = int( seq_col ) - 1
    except:
        stop_err( "Invalid Sequence Column: %s." %str( seq_col ) )

    title_col_list = title_col.split( ',' )
    out = open( outfile, 'w' )
    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = ""
    i = 0
    
    for i, line in enumerate( open( infile ) ):
        error = False
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            fields = line.split( '\t' )
            fasta_title = []
            for j in title_col_list:
                try:
                    j = int( j ) - 1
                    fasta_title.append( fields[j] )
                except:
                    skipped_lines += 1
                    if not invalid_line:
                        first_invalid_line = i + 1
                        invalid_line = line
                    error = True
                    break
            if not error:
                try:
                    fasta_seq = fields[seq_col]
                    if fasta_title[0].startswith( ">" ):
                        fasta_title[0] = fasta_title[0][1:]
                    print >> out, ">%s\n%s" % ( "_".join( fasta_title ), fasta_seq )
                except:
                    skipped_lines += 1
                    if not invalid_line:
                        first_invalid_line = i + 1
                        invalid_line = line
    out.close()    

    if skipped_lines > 0:
        print 'Data issue: skipped %d blank or invalid lines starting at #%d: "%s"' % ( skipped_lines, first_invalid_line, invalid_line )

if __name__ == "__main__" : __main__()