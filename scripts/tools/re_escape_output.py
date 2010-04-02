#!/usr/bin/env python

"""
Escapes a file into a form suitable for use with tool tests using re_match or re_match_multiline (when -m/--multiline option is used)

usage: re_escape_output.py [options] input_file [output_file]
    -m: Use Multiline Matching
"""

import optparse, re

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( "-m", "--multiline", action="store_true", dest="multiline", default=False, help="Use Multiline Matching")
    ( options, args ) = parser.parse_args()
    input = open( args[0] ,'rb' )
    if len( args ) > 1:
        output = open( args[1], 'wb' )
    else:
        if options.multiline:
            suffix = 're_match_multiline'
        else:
            suffix = 're_match'
        output = open( "%s.%s" % ( args[0], suffix ), 'wb' )
    if options.multiline:
        lines = [ re.escape( input.read() ) ]
    else:
        lines = [ "%s\n" % re.escape( line.rstrip( '\n\r' ) ) for line in input ]
    output.writelines( lines )
    output.close()

if __name__ == "__main__":
    __main__()
