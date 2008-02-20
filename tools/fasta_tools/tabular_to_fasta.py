#! /usr/bin/python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""

import sys, os

seq_hash = {}

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
        stop_err( "Invalid Sequence Column: %s." %seq_col )

    title_col_list = title_col.split( ',' )
    out = open( outfile, 'w' )

    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\n' )
        fields = line.split()
        fasta_title = []
        for j in title_col_list:
            j = int( j ) - 1
            if ( j < len( fields ) ):
                fasta_title.append( fields[j] )
        fasta_seq = fields[seq_col]
        if ( fasta_title[0].startswith(">") ):
            fasta_title[0] = fasta_title[0][1:]
        print >> out, ">%s\n%s" % ( "_".join( fasta_title ), fasta_seq )
    out.close()    

if __name__ == "__main__" : __main__()