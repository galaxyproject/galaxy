#!/usr/bin/env python

"""
Convert from GFF file to interval index file.

usage:
    python gff_to_interval_index_converter.py [input] [output]
"""
from __future__ import division

import fileinput
import sys

from bx.interval_index_file import Indexes

from galaxy.datatypes.util.gff_util import convert_gff_coords_to_bed, GenomicInterval, GFFReaderWrapper


def main():
    # Arguments
    input_fname, out_fname = sys.argv[1:]

    # Do conversion.
    index = Indexes()
    offset = 0
    reader_wrapper = GFFReaderWrapper( fileinput.FileInput( input_fname ), fix_strand=True )
    for feature in list( reader_wrapper ):
        # Add feature; index expects BED coordinates.
        if isinstance( feature, GenomicInterval ):
            convert_gff_coords_to_bed( feature )
            index.add( feature.chrom, feature.start, feature.end, offset )

        # Always increment offset, even if feature is not an interval and hence
        # not included in the index.
        offset += feature.raw_size

    index.write( open(out_fname, "w") )


if __name__ == "__main__":
    main()
