#!/usr/bin/env python

"""
Uses pysam to index a bgzipped interval file with tabix
Supported presets: bed, gff, vcf

usage: %prog in_file out_file
"""

from galaxy import eggs
import pkg_resources; pkg_resources.require( "pysam" )
import ctabix, subprocess, tempfile, sys, os, optparse

def main():
    # Read options, args.
    parser = optparse.OptionParser()
    parser.add_option( '-c', '--chr-col', type='int', dest='chrom_col' )
    parser.add_option( '-s', '--start-col', type='int', dest='start_col' )
    parser.add_option( '-e', '--end-col', type='int', dest='end_col' )
    parser.add_option( '-P', '--preset', dest='preset' )
    (options, args) = parser.parse_args()
    input_fname, index_fname, out_fname = args

    # Create index.
    if options.preset:
        # Preset type.
        ctabix.tabix_index(filename=index_fname, preset=options.preset, keep_original=True,
                           already_compressed=True, index_filename=out_fname)
    else:
        # For interval files; column indices are 0-based.
        ctabix.tabix_index(filename=index_fname, seq_col=(options.chrom_col - 1),
                           start_col=(options.start_col - 1), end_col=(options.end_col - 1),
                           keep_original=True, already_compressed=True, index_filename=out_fname)
    if os.path.getsize(index_fname) == 0:
        sys.stderr.write("The converted tabix index file is empty, meaning the input data is invalid.")

if __name__ == "__main__":
    main()
