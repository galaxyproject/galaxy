#!/usr/bin/env python
"""
Convert from VCF file to interval index file.
"""

import optparse

import galaxy_utils.sequence.vcf
from bx.interval_index_file import Indexes


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    in_file, out_file = args

    # Do conversion.
    index = Indexes()
    with open(in_file) as in_fh:
        reader = galaxy_utils.sequence.vcf.Reader(in_fh)
        offset = reader.metadata_len
        for vcf_line in reader:
            # VCF format provides a chrom and 1-based position for each variant.
            # IntervalIndex expects 0-based coordinates.
            index.add(vcf_line.chrom, vcf_line.pos - 1, vcf_line.pos, offset)
            offset += len(vcf_line.raw_line)

    with open(out_file, "wb") as out_fh:
        index.write(out_fh)


if __name__ == "__main__":
    main()
