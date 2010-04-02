#!/usr/bin/env python
"""
Input: fasta, int
Output: tabular
Return titles with lengths of corresponding seq
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    
    infile = sys.argv[1]
    out = open( sys.argv[2], 'w')
    keep_first_char = int( sys.argv[3] )

    fasta_title = ''
    seq_len = 0

    # number of char to keep in the title
    if keep_first_char == 0:
        keep_first_char = None
    else:
        keep_first_char += 1

    first_entry = True

    for line in open( infile ):
        line = line.strip()
        if not line or line.startswith( '#' ):
            continue
        if line[0] == '>':
            if first_entry == False:
                out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first_char ], seq_len ) )
            else:
                first_entry = False
            fasta_title = line
            seq_len = 0
        else:
            seq_len += len(line)

    # last fasta-entry
    out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first_char ], seq_len ) )
    out.close()

if __name__ == "__main__" : __main__()