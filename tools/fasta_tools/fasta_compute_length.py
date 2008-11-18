#! /usr/bin/python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    keep_first = int( sys.argv[3] )
    tmp_title = tmp_seq = ''
    tmp_seq_count = 0
    seq_hash = {}

    if keep_first == 0:
        keep_first = None
    else:
        keep_first += 1    

    for i, line in enumerate( file( input_filename ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        if line[0] == '>':
            if len( tmp_seq ) > 0:
                tmp_seq_count += 1
                seq_hash[ ( tmp_seq_count, tmp_title ) ] = tmp_seq
            tmp_title = line
            tmp_seq = ''
        else:
            tmp_seq = "%s%s" % ( tmp_seq, line )
            if line.split() and line.split()[0].isdigit():
                tmp_seq = "%s " % tmp_seq
    if len( tmp_seq ) > 0:
        seq_hash[ ( tmp_seq_count, tmp_title ) ] = tmp_seq
    
    title_keys = seq_hash.keys()
    title_keys.sort()
    output_handle = open( output_filename, 'w' )
    for i, fasta_title in title_keys:
        tmp_seq = seq_hash[ ( i, fasta_title ) ]
        output_handle.write( "%s\t%d\n" % ( fasta_title[ 1:keep_first ], len( tmp_seq ) ) )
    output_handle.close()

if __name__ == "__main__" : __main__()