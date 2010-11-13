#!/usr/bin/env python
# Refactored on 11/13/2010 by Kanwei Li

import sys
import optparse

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():
    usage = """%prog [options]
    
options (listed below) default to 'None' if omitted
    """
    parser = optparse.OptionParser(usage=usage)
    
    parser.add_option(
        '--0x0001','--is_paired',
        choices = ( '0','1' ),
        dest='is_paired',
        metavar="<0|1>",
        help='The read is paired in sequencing')

    parser.add_option(
        '--0x0002','--is_proper_pair',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_proper_pair',
        help='The read is mapped in a proper pair')

    parser.add_option(
        '--0x0004','--is_unmapped',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_unmapped',
        help='The query sequence itself is unmapped')

    parser.add_option(
        '--0x0008','--mate_is_unmapped',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='mate_is_unmapped',
        help='The mate is unmapped')

    parser.add_option(
        '--0x0010','--query_strand',
        dest='query_strand',
        metavar="<0|1>",
        choices = ( '0','1' ),
        help='Strand of the query: 0 = forward, 1 = reverse.')

    parser.add_option(
        '--0x0020','--mate_strand',
        dest='mate_strand',
        metavar="<0|1>",
        choices = ('0','1'),
        help='Strand of the mate: 0 = forward, 1 = reverse.')

    parser.add_option(
        '--0x0040','--is_first',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_first',
        help='The read is the first read in a pair')

    parser.add_option(
        '--0x0080','--is_second',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_second',
        help='The read is the second read in a pair')

    parser.add_option(
        '--0x0100','--is_not_primary',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_not_primary',
        help='The alignment for the given read is not primary')

    parser.add_option(
        '--0x0200','--is_bad_quality',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_bad_quality',
        help='The read fails platform/vendor quality checks')

    parser.add_option(
        '--0x0400','--is_duplicate',
        choices = ( '0','1' ),
        metavar="<0|1>",
        dest='is_duplicate',
        help='The read is either a PCR or an optical duplicate')
        
    parser.add_option(
        '-f','--input_sam_file',
        metavar="INPUT_SAM_FILE",
        dest='input_sam',
        default = False,
        help='Name of the SAM file to be filtered. STDIN is default')
            
    parser.add_option(
        '-c','--flag_column',
        dest='flag_col',
        default = '2',
        help='Column containing SAM bitwise flag. 1-based')

    options, args = parser.parse_args()

    if options.input_sam:
		infile = open ( options.input_sam, 'r')
    else:
    	infile = sys.stdin
        
    opt_ary = [
        options.is_paired,
        options.is_proper_pair,
        options.is_unmapped,
        options.mate_is_unmapped,
        options.query_strand,
        options.mate_strand,
        options.is_first,
        options.is_second,
        options.is_not_primary,
        options.is_bad_quality,
        options.is_duplicate
    ]
    
    opt_map = { '0': False, '1': True }
    used_indices = [(index, opt_map[opt]) for index, opt in enumerate(opt_ary) if opt is not None]
    flag_col = int( options.flag_col ) - 1
    
    for line in infile:
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            fields = line.split( '\t' )
            flags = int( fields[flag_col] )
            
            valid_line = True
            for index, opt_bool in used_indices:
                if bool(flags & 0x0001 << index) != opt_bool:
                    valid_line = False
                    break
                    
            if valid_line:
                print line

if __name__ == "__main__": main()

