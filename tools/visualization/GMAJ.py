#!/usr/bin/env python

"""
Script that Creates a zip file for use by GMAJ
"""
import sys, zipfile

def __main__():
    #create a new zip file
    out_file  = zipfile.ZipFile( sys.argv[1], "w" )
    #add info files
    out_file.write( sys.argv[3], "input.gmaj" ) #THIS FILE MUST BE ADDED FIRST
    out_file.write( sys.argv[2], "input.maf" )
    
    #add annotation files
    for line in open( sys.argv[4] ):
        try:
            out_file.write( *[ field.strip() for field in line.split( "=", 1 ) ] )
        except:
            continue
    out_file.close()

if __name__ == "__main__": __main__()
