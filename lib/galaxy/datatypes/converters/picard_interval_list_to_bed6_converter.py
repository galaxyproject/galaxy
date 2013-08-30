#!/usr/bin/env python
#Dan Blankenberg

import sys

assert sys.version_info[:2] >= ( 2, 5 )
HEADER_STARTS_WITH = ( '@' )

def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    header_lines = 0
    out = open( output_name, 'w' )
    i = 0
    for i, line in enumerate( open( input_name ) ):
        complete_interval = False
        line = line.rstrip( '\r\n' )
        if line:
            if line.startswith( HEADER_STARTS_WITH ):
                header_lines += 1
            else:
                try:
                    elems = line.split( '\t' )
                    if len( elems ) >= 5:
                        complete_interval = True
                    out.write( '%s\t%s\t%s\t%s\t0\t%s\n' % ( elems[0], int(elems[1])-1, elems[2], elems[4], elems[3] ) )
                except Exception, e:
                    print e
                    skipped_lines += 1
                    if not first_skipped_line:
                        first_skipped_line = i + 1
        else:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = i + 1
    out.close()
    info_msg = "%i lines converted to BED.  " % ( i + 1 - skipped_lines )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % ( skipped_lines, first_skipped_line )
    print info_msg

if __name__ == "__main__": __main__()
