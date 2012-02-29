#!/usr/bin/env python

"""
Uses pysam to bgzip a vcf file as-is. 
Headers, which are important, are kept.
Original ordering, which may be specifically needed  by tools or external display applications, is also maintained.

usage: %prog in_file out_file
"""

from galaxy import eggs
import pkg_resources; pkg_resources.require( "pysam" )
import ctabix, optparse

def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    input_fname, output_fname = args
    
    ctabix.tabix_compress(input_fname, output_fname, force=True)
    
if __name__ == "__main__": 
    main()
