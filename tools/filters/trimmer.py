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
        '-a','--ascii',
        dest='ascii',
        action='store_true',
        default = False,
        help='Use ascii codes to defined ignored beginnings instead of raw characters')
        
    parser.add_option(
        '-q','--fastq',
        dest='fastq',
        action='store_true',
        default = False,
        help='The input data in fastq format. It selected the script skips every even line since they contain sequence ids')

    parser.add_option(
        '-i','--ignore',
        dest='ignore',
        help='A comma separated list on ignored beginnings (e.g., ">,@"), or its ascii codes (e.g., "60,42") if option -a is enabled')

    parser.add_option(
        '-s','--start',
        dest='start',
        default = '0',
        help='Trim from beginning to here (1-based)')

    parser.add_option(
        '-e','--end',
        dest='end',
        default = '0',
        help='Trim from here to the ned (1-based)')

    parser.add_option(
        '-f','--file',
        dest='input_txt',
        default = False,
        help='Name of file to be chopped. STDIN is default')
            
    parser.add_option(
        '-c','--column',
        dest='col',
        default = '0',
        help='Column to chop. If 0 = chop the whole line')
       

    options, args = parser.parse_args()
    invalid_starts = []

    if options.input_txt:
		infile = open ( options.input_txt, 'r')
    else:
    	infile = sys.stdin
    	
    if options.ignore and options.ignore != "None":
        invalid_starts = options.ignore.split(',')
        
    if options.ascii and options.ignore and options.ignore != "None":
        for i, item in enumerate( invalid_starts ):
            invalid_starts[i] = chr( int( item ) )

    col = int( options.col )
 
    for i, line in enumerate( infile ):
        line = line.rstrip( '\r\n' )
        if line:
            
            if options.fastq and i % 2 == 0:
                print line
                continue
                

            if line[0] not in invalid_starts:
                if col == 0:
                    if int( options.end ) > 0:
                        line = line[ int( options.start )-1 : int( options.end ) ]
                    elif int( options.end ) < 0:
                        endposition = len(line)+int( options.end )
                        line = line[ int( options.start )-1  :  endposition  ]
                    else:
                        line = line[ int( options.start )-1 : ]
                else:
                    fields = line.split( '\t' )
                    if col-1 > len( fields ):
                        stop_err('Column %d does not exist. Check input parameters\n' % col)
                        
                    if int( options.end ) > 0:
                        fields[col - 1] = fields[col - 1][ int( options.start )-1 : int( options.end ) ]
                    elif int( options.end ) < 0:
                        endposition = len(fields[col - 1])+int( options.end )
                        fields[col - 1] = fields[col - 1][ int( options.start )-1 :  endposition  ]
                    else:
                        fields[col - 1] = fields[col - 1][ int( options.start )-1 : ]
                    line = '\t'.join(fields)
            print line   

if __name__ == "__main__": main()

