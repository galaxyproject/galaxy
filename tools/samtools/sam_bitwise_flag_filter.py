#!/usr/bin/env python

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

    parser.add_option(
        '-d','--debug',
        dest='debug',
        action='store_true',
        default = False,
        help='Print debugging info')

    options, args = parser.parse_args()

    if options.input_sam:
		infile = open ( options.input_sam, 'r')
    else:
    	infile = sys.stdin

    option_values = { '0': False, '1': True, None: None } 

    states = [];
    states.append( option_values[ options.is_paired ] )
    states.append( option_values[ options.is_proper_pair ] )
    states.append( option_values[ options.is_unmapped ] )
    states.append( option_values[ options.mate_is_unmapped ] )
    states.append( option_values[ options.query_strand ] )
    states.append( option_values[ options.mate_strand ] )
    states.append( option_values[ options.is_first ] )
    states.append( option_values[ options.is_second ] )
    states.append( option_values[ options.is_not_primary ] )
    states.append( option_values[ options.is_bad_quality ] )
    states.append( option_values[ options.is_duplicate ] )

    for line in infile:
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            fields = line.split( '\t' )
            sam_states = []
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0001 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0002 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0004 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0008 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0010 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0020 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0040 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0080 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0100 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0200 ) )
            sam_states.append( bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0400 ) )
            
            joined_states =  zip(states,sam_states)
            searchable_fields = []
            
            for i in range( len( joined_states ) ):
                if joined_states[i][0] != None: 
                    searchable_fields.append( joined_states[ i ] )
            
            valid_line = True
            
            for i in range( len( searchable_fields ) ):
                if searchable_fields[i][0] != searchable_fields[i][1]:
                    valid_line = False
                    
            if valid_line:
                print line
                if options.debug:
                    for i in range( len( joined_states ) ):
                        print i, joined_states[i][0], joined_states[i][1]
            
#    if skipped_lines > 0:
#        print 'Skipped %d invalid lines' % skipped_lines


if __name__ == "__main__": main()

