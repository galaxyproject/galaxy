#!/usr/bin/env python

"""
Uses pysam to index a bgzipped interval file with tabix
Supported presets: bed, gff, vcf

usage: %prog in_file out_file
"""
import optparse
import os
import sys

import pysam


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    parser.add_option("-c", "--chr-col", type="int", dest="chrom_col")
    parser.add_option("-s", "--start-col", type="int", dest="start_col")
    parser.add_option("-e", "--end-col", type="int", dest="end_col")
    parser.add_option("-P", "--preset", dest="preset")
    (options, args) = parser.parse_args()
    _, bgzip_fname, out_fname = args
    to_tabix(
        bgzip_fname=bgzip_fname,
        out_fname=out_fname,
        preset=options.preset,
        chrom_col=options.chrom_col,
        start_col=options.start_col,
        end_col=options.end_col,
    )


def to_tabix(bgzip_fname, out_fname, preset=None, chrom_col=None, start_col=None, end_col=None):
    # Create index.
    if preset:
        # Preset type.
        bgzip_fname = pysam.tabix_index(
            filename=bgzip_fname, preset=preset, keep_original=True, index=out_fname, force=True
        )
    else:
        # For interval files; column indices are 0-based.
        bgzip_fname = pysam.tabix_index(
            filename=bgzip_fname,
            seq_col=(chrom_col - 1),
            start_col=(start_col - 1),
            end_col=(end_col - 1),
            keep_original=True,
            index=out_fname,
            force=True,
        )
    if os.path.getsize(out_fname) == 0:
        sys.exit("The converted tabix index file is empty, meaning the input data is invalid.")
    return bgzip_fname


if __name__ == "__main__":
    main()
