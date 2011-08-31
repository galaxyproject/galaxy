#!/usr/bin/env python

import sys
import optparse
import re

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():
    usage = """%prog [options]
    
options (listed below) default to 'None' if omitted
    """
    parser = optparse.OptionParser(usage=usage)

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
        '-s','--start_column',
        dest='start_col',
        default = '4',
        help='Column containing position. 1-based')

    parser.add_option(
        '-g','--cigar_column',
        dest='cigar_col',
        default = '6',
        help='Column containing CIGAR or extended CIGAR string')

    parser.add_option(
        '-r','--ref_column',
        dest='ref_col',
        default = '3',
        help='Column containing name of the reference sequence coordinate. 1-based')
        
    parser.add_option(
        '-e','--read_column',
        dest='read_col',
        default = '1',
        help='Column containing read name. 1-based')

    parser.add_option(
        '-p','--print_all',
        dest='prt_all',
        action='store_true',
        default = False,
        help='Print coordinates and original SAM?')
    
    options, args = parser.parse_args()

    if options.input_sam:
        infile = open ( options.input_sam, 'r')
    else:
        infile = sys.stdin

    cigar = re.compile( '\d+M|\d+N|\d+D|\d+P' )

    print '#chrom\tstart\tend\tstrand\tread_name' # provide a (partial) header so that strand is automatically set in metadata

    for line in infile:
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ) and not line.startswith( '@' ) :
            fields = line.split( '\t' )
            start = int( fields[ int( options.start_col ) - 1 ] ) - 1
            end = 0
            for op in cigar.findall( fields[ int( options.cigar_col) - 1 ] ):
                end += int( op[ 0:len( op ) - 1 ] )
                
            strand = '+' 
            if bool( int( fields[ int( options.flag_col ) - 1 ] ) & 0x0010 ):
                strand = '-'
            read_name = fields[ int( options.read_col ) - 1 ]
            ref_name  = fields[ int( options.ref_col ) - 1 ]
            
            if ref_name != '*':
                # Do not print lines with unmapped reads that contain '*' instead of chromosome name        
                if options.prt_all: 
                    print '%s\t%s\t%s\t%s\t%s' % (ref_name, str(start), str(end+start), strand, line)
                else:
                    print '%s\t%s\t%s\t%s\t%s' % (ref_name, str(start), str(end+start), strand, read_name)

if __name__ == "__main__": main()

