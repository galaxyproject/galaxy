#!/usr/bin/env python2.4
#Guruprasad Ananda
"""
Extract features from GFF file.

usage: %prog input1 out_file1 column features
"""

import sys, os

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        inp_file, out_file, column, features = args
    except:
        stop_err("One or more arguments is missing or invalid.\nUsage: prog input output column features")
    
    try:
        column = int(column)
    except:
        stop_err("%s is an invalid column." %(column))
    
    if features == None:
        stop_err( "Column %d has no features to display. Please select another column." %(column+1))

    try:
        fo=open(out_file,'w')
        for line in open(inp_file):
            if line[0] == '#' or not(line) or line == "":
                print >>fo, line.strip()
                continue
            try:
                if line.split('\t')[column] in features.split(','):
                    print >>fo, line.strip()
            except:
                pass
        fo.close()
    except Exception, exc:
        print >> sys.stderr, exc
            
    print 'Field = Column %d and Features = %s' %(column+1, features)

if __name__ == "__main__":
    main()       
