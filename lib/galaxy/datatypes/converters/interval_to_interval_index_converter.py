#!/usr/bin/env python

"""
Convert from interval file to interval index file.

usage: %prog <options> in_file out_file
    -c, --chr-col: chromosome column, default=1
    -s, --start-col: start column, default=2
    -e, --end-col: end column, default=3
"""

import optparse

from bx.interval_index_file import Indexes


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    parser.add_option("-c", "--chr-col", type="int", dest="chrom_col", default=1)
    parser.add_option("-s", "--start-col", type="int", dest="start_col", default=2)
    parser.add_option("-e", "--end-col", type="int", dest="end_col", default=3)
    (options, args) = parser.parse_args()
    input_fname, output_fname = args

    # Make column indices 0-based.
    options.chrom_col -= 1
    options.start_col -= 1
    options.end_col -= 1

    # Do conversion.
    index = Indexes()
    offset = 0
    with open(input_fname) as in_fh:
        for line in in_fh:
            feature = line.strip().split()
            if not feature or feature[0].startswith("track") or feature[0].startswith("#"):
                offset += len(line)
                continue
            chrom = feature[options.chrom_col]
            chrom_start = int(feature[options.start_col])
            chrom_end = int(feature[options.end_col])
            index.add(chrom, chrom_start, chrom_end, offset)
            offset += len(line)

    with open(output_fname, "wb") as out:
        index.write(out)


if __name__ == "__main__":
    main()
