#!/usr/bin/env python
#Guruprasad Ananda
"""
Extract features from GFF file.

usage: %prog input1 out_file1 column features
"""

import sys, os

from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        inp_file, out_file, column, features = args
    except:
        stop_err( "One or more arguments is missing or invalid.\nUsage: prog input output column features" )
    try:
        column = int( column )
    except:
        stop_err( "Column %s is an invalid column." % column )
    
    if features == None:
        stop_err( "Column %d has no features to display, select another column." %( column + 1 ) )

    fo=open( out_file, 'w' )
    for i, line in enumerate( file( inp_file ) ):
        line = line.rstrip( '\r\n' )
        if line and line.startswith( '#' ):
            # Keep valid comment lines in the output
            fo.write( "%s\n" % line )
        else:
            try:
                if line.split( '\t' )[column] in features.split( ',' ):
                    fo.write( "%s\n" % line )
            except:
                pass
    fo.close()
            
    print 'Column %d features: %s' %( column + 1, features )

if __name__ == "__main__":
    main()       
