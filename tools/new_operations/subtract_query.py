#!/usr/bin/env python2.4
# Greg Von Kuster

"""
Subtract an entire query from another query
usage: %prog in_file_1 in_file_2 out_file
"""

import sys, sets
import cookbook.doc_optparse


def get_lines(fname):
    i = 0
    lines = set([])
    for i, line in enumerate(file(fname)):
        line = line.strip()
        lines.add( line )
    return (i+1, lines)

def main():   
    # Parsing Command Line here
    options, args = cookbook.doc_optparse.parse( __doc__ )
    
    try:
        inp1_file, inp2_file, out_file = args
    except:
        cookbook.doc_optparse.exception()

    try:
        fo = open(out_file,'w')
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()

    len1, lines1 = get_lines(inp1_file)
    diff1 = len1 - len(lines1)
    len2, lines2 = get_lines(inp2_file)
    
    lines1.difference_update(lines2)
    
    for line in lines1:
        print >> fo, line

    fo.close()

    if diff1 > 0:
        print "Eliminated %d duplicate lines from first query." %diff1

if __name__ == "__main__":
    main()
