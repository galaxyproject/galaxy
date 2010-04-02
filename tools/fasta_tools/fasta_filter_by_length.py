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
    output_handle = open( output_filename, 'w' )
    tmp_size = 0 #-1
    tmp_buf = ''
    at_least_one = 0
    for line in file(input_filename):
        if not line or line.startswith('#'):
            continue
        if line[0] == '>':
            if min_length <= tmp_size <= max_length or (min_length <= tmp_size and max_length == 0):
                output_handle.write(tmp_buf)
                at_least_one = 1
            tmp_buf = line
            tmp_size = 0                                                       
        else:
            if max_length == 0 or tmp_size < max_length:
                tmp_size += len(line.rstrip('\r\n'))
                tmp_buf += line
    # final flush of buffer
    if min_length <= tmp_size <= max_length or (min_length <= tmp_size and max_length == 0):
        output_handle.write(tmp_buf.rstrip('\r\n'))
        at_least_one = 1
    output_handle.close()
    if at_least_one == 0:
        print "There is no sequence that falls within your range."

if __name__ == "__main__" : __main__()
