#!/usr/bin/env python
# This code exists in 2 places: ~/datatypes/converters and ~/tools/fasta_tools
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""

import sys, os

seq_hash = {}

def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]
    title = ''
    sequence = ''
    sequence_count = 0
    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if line.startswith( '>' ):
            if sequence:
                sequence_count += 1
                seq_hash[( sequence_count, title )] = sequence
            title = line
            sequence = ''
        else:
            if line:
                sequence += line
                if line.split() and line.split()[0].isdigit():
                    sequence += ' '
    if sequence:
        seq_hash[( sequence_count, title )] = sequence
    # return only those lengths are in the range
    out = open( outfile, 'w' )
    title_keys = seq_hash.keys()
    title_keys.sort()
    for i, fasta_title in title_keys:
        sequence = seq_hash[( i, fasta_title )]
        print >> out, "%s\t%s" %( fasta_title, sequence )
    out.close()

if __name__ == "__main__" : __main__()
