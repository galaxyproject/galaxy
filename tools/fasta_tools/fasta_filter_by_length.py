#! /usr/bin/python
"""
Input: fasta, minimal length, maximal length
Output: fasta
Return sequences whose lengths are within the range.
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    
    infile = sys.argv[1]
    try:
        min_length = int( sys.argv[2] )
    except:
        stop_err( "Minimal length of the return sequence requires a numerical value." )
    try:
        max_length = int( sys.argv[3] )
    except:
        stop_err( "Maximum length of the return sequence requires a numerical value." )
    outfile = sys.argv[4]
    fasta_title = fasta_seq = ''
    at_least_one = 0
    
    out = open( outfile, 'w' )

    for i, line in enumerate( file( infile ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        
        if line[0] == '>':
            if len( fasta_seq ) > 0:

                if max_length <= 0: 
                    compare_max_length = len( fasta_seq ) + 1
                else:
                    compare_max_length = max_length
                    
                l = len( fasta_seq )
                
                if l >= min_length and l <= compare_max_length:
                    at_least_one += 1
                    out.write( "%s\n" % fasta_title )
                    c = 0
                    s = fasta_seq
                    while c < l:
                        b = min( c + 50, l )
                        out.write( "%s\n" % s[ c:b ] )   
                        c = b
                                        
            fasta_title = line
            fasta_seq = ''
        else:
            fasta_seq = "%s%s" % ( fasta_seq, line ) 
    
    if len( fasta_seq ) > 0:
                
        if max_length <= 0: 
            compare_max_length = len( fasta_seq ) + 1
        else:
            compare_max_length = max_length
            
        l = len( fasta_seq )
        
        if l >= min_length and l <= compare_max_length:
            at_least_one += 1
            out.write( "%s\n" % fasta_title )
            c = 0
            s = fasta_seq
            while c < l:
                b = min( c + 50, l )
                out.write( "%s\n" % s[ c:b ] )   
                c = b

    out.close()

    if at_least_one == 0:
        print "There is no sequence that falls within your range."


if __name__ == "__main__" : __main__()