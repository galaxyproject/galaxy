#!/usr/bin/env python
# Greg Von Kuster

"""
Subtract an entire query from another query
usage: %prog in_file_1 in_file_2 begin_col end_col output 
"""
import sys, re
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

assert sys.version_info[:2] >= ( 2, 4 )

def get_lines(fname, begin_col='', end_col=''):
    lines = set([])
    i = 0
    for i, line in enumerate(file(fname)):
        line = line.rstrip('\r\n')
        if line and not line.startswith('#'):
            if begin_col and end_col:
                """Both begin_col and end_col must be integers at this point."""
                try:
                    line = line.split('\t')
                    line = '\t'.join([line[j] for j in range(begin_col-1, end_col)])
                    lines.add( line )
                except: pass
            else:
                lines.add( line )
    if i: return (i+1, lines)
    else: return (i, lines)

def main():
    
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )

    try:
        inp1_file, inp2_file, begin_col, end_col, out_file = args
    except:
        doc_optparse.exception()
    
    begin_col = begin_col.strip()
    end_col = end_col.strip()
    
    if begin_col != 'None' or end_col != 'None':
        """
        The user selected columns for restriction.  We'll allow default
        values for both begin_col and end_col as long as the user selected
        at least one of them for restriction.
        """
        if begin_col == 'None':
            begin_col = end_col
        elif end_col == 'None':
            end_col = begin_col
        begin_col = int(begin_col)
        end_col = int(end_col)
        """Make sure that begin_col <= end_col (switch if not)"""
        if begin_col > end_col:
            tmp_col = end_col
            end_col = begin_col
            begin_col = tmp_col
    else:
        begin_col = end_col = ''

    try:
        fo = open(out_file,'w')
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()

    """
    len1 is the number of lines in inp1_file
    lines1 is the set of unique lines in inp1_file
    diff1 is the number of duplicate lines removed from inp1_file
    """
    len1, lines1 = get_lines(inp1_file, begin_col, end_col)
    diff1 = len1 - len(lines1)
    len2, lines2 = get_lines(inp2_file, begin_col, end_col)
    
    lines1.difference_update(lines2)
    """lines1 is now the set of unique lines in inp1_file - the set of unique lines in inp2_file"""

    for line in lines1:
        print >> fo, line

    fo.close()
    
    info_msg = 'Subtracted %d lines. ' %((len1 - diff1) - len(lines1))
    
    if begin_col and end_col:
        info_msg += 'Restricted to columns c' + str(begin_col) + ' thru c' + str(end_col) + '. '

    if diff1 > 0:
        info_msg += 'Eliminated %d duplicate/blank/comment/invalid lines from first query.' %diff1
    
    print info_msg

if __name__ == "__main__":
    main()
