#!/usr/bin/env python
# Variants of this code exists in 2 places, this file which has no
# user facing options which is called for implicit data conversion,
# lib/galaxy/datatypes/converters/fasta_to_tabular_converter.py
# and the user-facing Galaxy tool of the same name which has many
# options. That version is now on GitHub and the Galaxy Tool Shed:
# https://github.com/galaxyproject/tools-devteam/tree/master/tools/fasta_to_tabular
# https://toolshed.g2.bx.psu.edu/view/devteam/fasta_to_tabular
"""
Input: fasta
Output: tabular
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
            # Strip off the leading '>' and remove any pre-existing
            # tabs which would trigger extra columns:
            title = line[1:].replace('\t', ' ')
            sequence = ''
        else:
            if line:
                sequence += line
                if line.split() and line.split()[0].isdigit():
                    sequence += ' '
    if sequence:
        seq_hash[( sequence_count, title )] = sequence
    out = open( outfile, 'w' )
    title_keys = seq_hash.keys()
    title_keys.sort()
    for i, fasta_title in title_keys:
        sequence = seq_hash[( i, fasta_title )]
        print >> out, "%s\t%s" %( fasta_title, sequence )
    out.close()

if __name__ == "__main__" : __main__()
