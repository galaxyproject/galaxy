#!/usr/bin/env python
# code is same as ~/tools/stats/wiggle_to_simple.py
"""
Read a wiggle track and print out a series of lines containing
"chrom position score". Ignores track lines, handles bed, variableStep
and fixedStep wiggle lines.
"""
from __future__ import print_function

import sys

import bx.wiggle

from galaxy.util.ucsc import UCSCOutWrapper, UCSCLimitException


def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()


def main():
    if len( sys.argv ) > 1:
        in_file = open( sys.argv[1] )
    else:
        in_file = open( sys.stdin )

    if len( sys.argv ) > 2:
        out_file = open( sys.argv[2], "w" )
    else:
        out_file = sys.stdout

    try:
        for fields in bx.wiggle.IntervalReader( UCSCOutWrapper( in_file ) ):
            out_file.write( "%s\n" % "\t".join( map( str, fields ) ) )
    except UCSCLimitException:
        # Wiggle data was truncated, at the very least need to warn the user.
        print('Encountered message from UCSC: "Reached output limit of 100000 data values", so be aware your data was truncated.')
    except ValueError as e:
        in_file.close()
        out_file.close()
        stop_err( str( e ) )

    in_file.close()
    out_file.close()


if __name__ == "__main__":
    main()
