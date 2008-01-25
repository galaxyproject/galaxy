#!/usr/bin/env python2.4
# This code exists in 2 places: ~/datatypes/converters and ~/tools/filters
import sys

def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name, 'w' )
    out.write( "## gff-version 2\n" )
    out.write( "## bed_to_gff_converter.py\n\n" )
    for i, line in enumerate( file( input_name ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ) and not line.startswith( 'track' ) and not line.startswith( 'browser' ):
            try:
                elems = line.split( '\t' )
                start = str( int( elems[1] ) + 1 )
                try:
                    feature = elems[3]
                except:
                    feature = 'feature_%d' % ( i + 1 )
                try:
                    score = elems[4]
                except:
                    score = '0'
                # Wouldn't it be better to use the score if it exists rather then hard-coding the '.'?
                # The same goes for strand, rather than hard-coding the '+'.
                # I also wonder why each line ends in a semi-colon.
                # I'm keeping thigs as they were in the original perl code in order to not break workflow.
                out.write( '%s\tbed2gff\t%s\t%s\t%s\t.\t+\t.\tscore "%s";\n' % ( elems[0], feature, start, elems[2], score ) )
            except:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
        else:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = i + 1
    out.close()
    info_msg = "%i lines converted to GFF version 2.  " % ( i + 1 - skipped_lines )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." %( skipped_lines, first_skipped_line )
    print info_msg

if __name__ == "__main__": __main__()
