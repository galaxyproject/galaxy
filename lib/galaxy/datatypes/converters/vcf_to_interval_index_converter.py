#!/usr/bin/env python

"""
Convert from VCF file to interval index file.
"""
from __future__ import division

import optparse

from bx.interval_index_file import Indexes

import galaxy_utils.sequence.vcf


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    in_file, out_file = args

    # Do conversion.
    index = Indexes()
    reader = galaxy_utils.sequence.vcf.Reader( open( in_file ) )
    offset = reader.metadata_len
    for vcf_line in reader:
        # VCF format provides a chrom and 1-based position for each variant.
        # IntervalIndex expects 0-based coordinates.
        index.add( vcf_line.chrom, vcf_line.pos - 1, vcf_line.pos, offset )
        offset += len( vcf_line.raw_line )

    index.write( open( out_file, "w" ) )


if __name__ == "__main__":
    main()
