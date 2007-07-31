#!/usr/bin/env python2.4

"""
Extract features from GFF file.

usage: %prog input1 out_file1 column features out_format
"""

import sys, os

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        inp_file, out_file, column, features = args
        column = int(column)
    except:
        doc_optparse.exception()
    
    if features == None:
        print "Column %d has no features to display. Please select another column." %(column+1)
        sys.exit()

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
