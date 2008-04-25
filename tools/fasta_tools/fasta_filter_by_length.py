#! /usr/bin/python
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
    
    input_filename = sys.argv[1]
    try:
        min_length = int( sys.argv[2] )
    except:
        stop_err( "Minimal length of the return sequence requires a numerical value." )
    try:
        max_length = int( sys.argv[3] )
    except:
        stop_err( "Maximum length of the return sequence requires a numerical value." )
    output_filename = sys.argv[4]
    tmp_title = tmp_seq = ''
    tmp_seq_count = 0
    seq_hash = {}

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
            if line.split()[0].isdigit():
                tmp_seq = "%s " % tmp_seq
    if len( tmp_seq ) > 0:
        seq_hash[ ( tmp_seq_count, tmp_title ) ] = tmp_seq
    
    title_keys = seq_hash.keys()
    title_keys.sort()
    output_handle = open( output_filename, 'w' )
    at_least_one = 0
    for i, fasta_title in title_keys:
        tmp_seq = seq_hash[ ( i, fasta_title ) ]
        if max_length <= 0: 
            compare_max_length = len( tmp_seq ) + 1
        else:
            compare_max_length = max_length
        l = len( tmp_seq )
        if l >= min_length and l <= compare_max_length:
            at_least_one += 1
            output_handle.write( "%s\n" % fasta_title )
            c = 0
            s = tmp_seq
            while c < l:
                b = min( c + 50, l )
                output_handle.write( "%s\n" % s[ c:b ] )   
                c = b
    output_handle.close()

    if at_least_one == 0:
        print "There is no sequence that falls within your range."


if __name__ == "__main__" : __main__()