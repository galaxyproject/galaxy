#!/usr/bin/env python
"""
Uses pysam to bgzip a file

usage: %prog in_file out_file
"""

import optparse
import os.path

import pysam


def main():
    # Read options, args.
    usage = "Usage: %prog [options] tabular_input_file bgzip_output_file"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-c', '--chr-col', type='int', default=0, dest='chrom_col')
    parser.add_option('-s', '--start-col', type='int', default=1, dest='start_col')
    parser.add_option('-e', '--end-col', type='int', default=1, dest='end_col')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage()
        exit(1)
    input_fname, output_fname = args
    output_dir = os.path.dirname(output_fname)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    pysam.tabix_compress(input_fname, output_fname, force=True)
    # Column indices are 0-based.
    pysam.tabix_index(output_fname, seq_col=options.chrom_col, start_col=options.start_col, end_col=options.end_col)


if __name__ == "__main__":
    main()
