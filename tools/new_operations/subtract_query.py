#!/usr/bin/env python2.4
# Greg Von Kuster

"""
Subtract an entire query from another query
usage: %prog in_file_1 in_file_2 begin_col end_col output 
    -n, --num_cols=N,N: Number of columns in tab-delimited files
"""

import sys, sets, re
import cookbook.doc_optparse
from galaxy.datatypes import sniff

def get_lines(fname, begin_col='', end_col=''):
    i = 0
    lines = set([])
    for i, line in enumerate(file(fname)):
        line = line.rstrip('\r\n')
        if begin_col and end_col:
            """
            Both begin_col and end_col must be integers at this point.
            """
            line = line.split('\t')
            line = '\t'.join([line[j] for j in range(begin_col-1, end_col)])
        lines.add( line )
    return (i+1, lines)

def main():
    
    # Parsing Command Line here
    options, args = cookbook.doc_optparse.parse( __doc__ )
    
    try:
        num_columns1, num_columns2 = options.num_cols.split(',')
    except:
        num_columns1 = num_columns2 = ''
    try:
        inp1_file, inp2_file, begin_col, end_col, out_file = args
    except:
        try:
            inp1_file, inp2_file, out_file = args
            begin_col = end_col = ''
        except:
            cookbook.doc_optparse.exception()
    
    """
    If we are to restrict to specific columns, make sure input datasets are tabular.
    We'll allow default values for both begin_col and end_col.  If the user enters a
    begin_col, but not an end_col, end_col will be set to input1_columns.  If the 
    user enters an end_col but not a begin_col, begin_col will be set to 1.
    """
    begin_col_is_valid = end_col_is_calid = False
    if begin_col or end_col:
        """
        First we'll determine if we have tabular queries.
        """
        is_tabular1 = sniff.is_column_based(inp1_file, sep='\t')
        is_tabular2 = sniff.is_column_based(inp2_file, sep='\t')
        if is_tabular1 and is_tabular2:
            try:
                num_columns1 = int(num_columns1)
                num_columns2 = int(num_columns2)
                are_tabular = True
            except:
                are_tabular = False
        else:
            are_tabular = False

        if are_tabular:
            """
            Next we'll ensure that the user entered valid begin_col and end_col
            values for the first query.
            """
            if begin_col and re.compile('c[0-9]+').findall(begin_col):
                try:
                    begin_col = int(begin_col[1:])
                    if begin_col > 0 and begin_col < num_columns1:
                        begin_col_is_valid = True
                    else:
                        begin_col_is_valid = False
                except:
                    begin_col_is_valid = False
            else:
                begin_col_is_valid = False
            if end_col and re.compile('c[0-9]+').findall(end_col):
                try:
                    end_col = int(end_col[1:])
                    if end_col > 1 and end_col <= num_columns1:
                        end_col_is_valid = True
                    else:
                        end_col_is_valid = False
                except:
                    end_col_is_valid = False
            else:
                end_col_is_valid = False
            """
            Next we'll set defaults for begin_col or end_col if the user
            left one (but not both) of them blank.
            """
            if begin_col_is_valid and not end_col:
                end_col = num_columns1
                end_col_is_valid = True
            elif not begin_col and end_col_is_valid:
                begin_col = 1
                begin_col_is_valid = True
            """
            Next we want to make sure that begin_col < end_col
            """
            if begin_col >= end_col:
                begin_col_is_valid = end_col_is_calid = False
            """
            Next we'll ensure that begin_col and end_col are valid
            for the second query.
            """
            if begin_col_is_valid and end_col_is_valid:
                if not begin_col < num_columns2:
                    begin_col_is_valid = False
                if not end_col <= num_columns2:
                    end_col_is_valid = False
            """
            Finally, if all is not well, we'll blank out begin_col and end_col.
            """
            if not (begin_col_is_valid and end_col_is_valid):
                begin_col = end_col = ''
        else:
            begin_col = end_col = ''

    try:
        fo = open(out_file,'w')
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()

    len1, lines1 = get_lines(inp1_file, begin_col, end_col)
    diff1 = len1 - len(lines1)
    len2, lines2 = get_lines(inp2_file, begin_col, end_col)
    
    lines1.difference_update(lines2)
    
    no_lines = 0
    for line in lines1:
        no_lines += 1
        print >> fo, line

    fo.close()

    info_msg = 'Subtracted %d lines. ' %(len1 - no_lines)

    if begin_col and end_col:
        info_msg += 'Restricted to columns c' + str(begin_col) + ' thru c' + str(end_col) + '. '

    if diff1 > 0:
        info_msg += 'Eliminated %d duplicate lines from first query.' %diff1
    
    print info_msg

if __name__ == "__main__":
    main()
