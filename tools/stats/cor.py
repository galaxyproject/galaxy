#!/usr/bin/env python

"""
Calculate correlations between numeric columns in a tab delim file.

usage: %prog infile output.txt columns method
"""

import sys
from Numeric import *
from rpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def main():

    method = sys.argv[4]
    assert method in ( "pearson", "kendall", "spearman" )

    try:
        columns = map( int, sys.argv[3].split( ',' ) )
    except:
        stop_err("Problem determining columns '%s'" %sys.argv[3])
    
    matrix = []
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = ''
    invalid_column = 0

    for i, line in enumerate( file( sys.argv[1] ) ):
        valid = True
        line = line.rstrip('\n\r')

        if line and not line.startswith( '#' ): 
            # Extract values and convert to floats
            row = []
            for column in columns:
                column -= 1
                fields = line.split( "\t" )
                if len( fields ) <= column:
                    valid = False
                else:
                    val = fields[column]
                    if val.lower() == "na": 
                        row.append( float( "nan" ) )
                    else:
                        try:
                            row.append( float( fields[column] ) )
                        except:
                            valid = False
                            skipped_lines += 1
                            invalid_value = fields[column]
                            invalid_column = column+1
                            if not first_invalid_line:
                                first_invalid_line = i+1
        else:
            valid = False
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = i+1

        if valid:
            matrix.append( row )

    if skipped_lines < i:

        try:
            out = open( sys.argv[2], "w" )
        except:
            print >> sys.stderr, "Unable to open output file"
            sys.exit()

        # Run correlation
        try:
            value = r.cor( array( matrix ), use="pairwise.complete.obs", method=method )
        except ValueError, exc:
            stop_err("Computing correlation resulted in error: %s." %exc)
        except IndexError, exc:
            stop_err("Computing correlation resulted in error: %s." %exc)

        for row in value:
            print >> out, "\t".join( map( str, row ) )

        out.close()

    if skipped_lines > 0:
        print "Skipped %d invalid lines starting with line #%d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )

if __name__ == "__main__":
    main()
