import sys, re

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    infile =  open ( sys.argv[1], 'r')
    cols   =  ( re.sub( '\s*','',sys.argv[2] ) ).split( ',' )
    outfile = open ( sys.argv[3], 'w')        

    for line in infile:
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            fields = line.split( '\t' )
            line += '\t'
            for col in cols:
                try:
                    line += fields[ int( col.lstrip( 'c' ) ) -1 ]
                except:
                    stop_err( 'Column %s does not appear in the input file' % str( col ) )
            print >>outfile, line
            
            
if __name__ == "__main__" : __main__()