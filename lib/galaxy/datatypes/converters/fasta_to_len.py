#!/usr/bin/env python
"""
Input: fasta, int
Output: tabular
Return titles with lengths of corresponding seq
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def compute_fasta_length( fasta_file, out_file, keep_first_char, keep_first_word=False ):

    infile = fasta_file
    out = open( out_file, 'w')
    keep_first_char = int( keep_first_char )

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
                if keep_first_word:
                    fasta_title = fasta_title.split()[0]
                out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first_char ], seq_len ) )
            else:
                first_entry = False
            fasta_title = line
            seq_len = 0
        else:
            seq_len += len(line)

    # last fasta-entry
    if keep_first_word:
        fasta_title = fasta_title.split()[0]
    out.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first_char ], seq_len ) )
    out.close()

if __name__ == "__main__" :
    compute_fasta_length( sys.argv[1], sys.argv[2], sys.argv[3], True )
