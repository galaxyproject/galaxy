#!/usr/bin/env python

"""
Convert from pileup file to interval index file.

usage: %prog <options> in_file out_file
"""

import optparse

from bx.interval_index_file import Indexes


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    input_fname, output_fname = args

    # Do conversion.
    index = Indexes()
    offset = 0
    with open(input_fname) as in_fh:
        for line in in_fh:
            chrom, start = line.split()[0:2]
            # Pileup format is 1-based.
            start = int(start) - 1
            index.add(chrom, start, start + 1, offset)
            offset += len(line)

    with open(output_fname, "wb") as out:
        index.write(out)


if __name__ == "__main__":
    main()
