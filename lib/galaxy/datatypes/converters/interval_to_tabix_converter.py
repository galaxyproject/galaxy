#!/usr/bin/env python

"""
Uses pysam to index a bgzipped interval file with tabix
Supported presets: bed, gff, vcf

usage: %prog in_file out_file
"""

from galaxy import eggs
import pkg_resources; pkg_resources.require( "pysam" )
import ctabix, subprocess, tempfile, sys, os

def main():
    # Read options, args.
    filetype, input_fname, index_fname, out_fname = sys.argv[1:]
    
    ctabix.tabix_index(filename=index_fname, preset=filetype, keep_original=True, already_compressed=True, index_filename=out_fname)
    if os.path.getsize(index_fname) == 0:
        sys.stderr.write("The converted tabix index file is empty, meaning the input data is invalid.")
    
if __name__ == "__main__": 
    main()
    