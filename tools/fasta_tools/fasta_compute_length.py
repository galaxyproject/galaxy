#! /usr/bin/python
"""
Input: fasta, int
Output: tabular
Return titles with lengths of corresponding seq
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    
    infile = sys.argv[1]
    outfile = sys.argv[2]
    keep_first = int( sys.argv[3] )
    
    fasta_title = fasta_seq = ''

    # number of char to keep in the title
    if keep_first == 0:
        keep_first = None
    else:
        keep_first += 1    

    out = open(outfile, 'w')
    
    for i, line in enumerate( file( infile ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        if line[0] == '>':
            if len( fasta_seq ) > 0 :
                out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first ], len( fasta_seq ) ) )
            fasta_title = line
            fasta_seq = ''
        else:
            fasta_seq = "%s%s" % ( fasta_seq, line )
            
    # check the last sequence
    if len( fasta_seq ) > 0:
        out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first ], len( fasta_seq ) ) )
            
    out.close()

if __name__ == "__main__" : __main__()