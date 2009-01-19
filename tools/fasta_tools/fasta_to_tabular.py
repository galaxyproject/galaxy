#! /usr/bin/python
# This code exists in 2 places: ~/datatypes/converters and ~/tools/fasta_tools
"""
Input: fasta, int
Output: tabular
format convert: fasta to tabular
"""

import sys, os

seq_hash = {}

def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]
    keep_first = int( sys.argv[3] )
    fasta_title = fasta_seq = ''
    
    if keep_first == 0:
        keep_first = None
    else:
        keep_first += 1

    out = open( outfile, 'w' )
    
    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        if line.startswith( '>' ):
            if fasta_seq:
                out.write( "%s\t%s\n" %( fasta_title[ 1:keep_first ], fasta_seq ) )
            fasta_title = line
            fasta_seq = ''
        else:
            if line:
                fasta_seq = "%s%s" % ( fasta_seq, line )

    if fasta_seq:
        out.write( "%s\t%s\n" %( fasta_title[ 1:keep_first ], fasta_seq ) )
                
    out.close()

if __name__ == "__main__" : __main__()