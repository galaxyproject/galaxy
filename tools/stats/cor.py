#!/usr/bin/env python

"""
Calculate covariance / correlations between numeric columns in a tab delim file.

usage: %prog infile output.txt cov_or_cor method columns
"""

import sys
from Numeric import *
from rpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def main():

    method = sys.argv[3]
    assert method in ( "pearson", "kendall", "spearman" )

    try:
        columns = map( int, sys.argv[4].split( ',' ) )
    except:
        print 'Columns "%s" are invalid. Refer to columns with a number starting at 1.' %sys.argv[4]
        sys.exit()
    
    matrix = []
    skipped_lines = 0
    first_invalid_line = 0
    invalid_value = None
    invalid_column = None

    for i, line in enumerate( open( sys.argv[1] ) ):
        line = line.strip()

        if line and not line.startswith( '#' ): 
            # Extract values and convert to floats
            row = []
            for column in columns:
                column -= 1
                fields = line.split( "\t" )
                if len( fields ) <= column:
                    #return stop_err( "No value in column %d on line %d." % ( column+1, i ) )
                    print "No value in column %d on line %d." % ( column+1, i )
                    sys.exit()
                val = fields[column]
                if val.lower() == "na": 
                    row.append( float( "nan" ) )
                else:
                    try:
                        row.append( float( fields[column] ) )
                    except ValueError:
                        #return fail( "Value '%s' in column %d on line %d is not numeric" % ( fields[column], column+1, i ) )
                        skipped_lines += 1
                        if not first_invalid_line:
                            invalid_value = fields[column]
                            invalid_column = column+1
                            first_invalid_line = i + 1
            matrix.append( row )

    if skipped_lines < i:
        # Run correlation
        value = r.cor( array( matrix ), use="pairwise.complete.obs", method=method )
    
        out = open( sys.argv[2], "w" )
        
        for row in value:
            print >> out, "\t".join( map( str, row ) )
        
        out.close()

    if skipped_lines > 0:
        print "Skipped %d invalid lines starting with line #%d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )

if __name__ == "__main__":
    main()
