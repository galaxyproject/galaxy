#!/usr/bin/env python
# This code exists in 2 places: ~/datatypes/converters and ~/tools/fasta_tools
"""
Input: fasta (input file), tabular (output file), int (truncation of id), int (columns from description)
Output: tabular
format convert: fasta to tabular
"""

import sys, os

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    if len(sys.argv) != 5:
        stop_err("Wrong number of argument. Expect four (fasta, tabular, truncation, columns)")
    infile = sys.argv[1]
    outfile = sys.argv[2]
    keep_first = int( sys.argv[3] )
    descr_split = int( sys.argv[4] )
    fasta_title = fasta_seq = ''
    if keep_first == 0:
        keep_first = None
    elif descr_split == 1:
        #Added one for the ">" character
        #(which is removed if using descr_split > 1)
        keep_first += 1
    if descr_split < 1:
        stop_err("Bad description split value (should be 1 or more)")
    out = open( outfile, 'w' )
    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        if line.startswith( '>' ):
            #Don't want any existing tabs to trigger extra columns:
            line = line.replace('\t', ' ')
            if i > 0:
                out.write('\n')
            if descr_split == 1:
                out.write(line[1:keep_first])
            else:
                words = line[1:].split(None, descr_split-1)
                #apply any truncation to first word (the id)
                words[0] = words[0][0:keep_first]
                #pad with empty columns if required
                words += [""]*(descr_split-len(words))
                out.write("\t".join(words))
            out.write('\t')
        else:
            out.write(line)
    if i > 0:
        out.write('\n')
    out.close()

if __name__ == "__main__" : __main__()
