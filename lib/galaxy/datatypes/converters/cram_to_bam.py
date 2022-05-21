#!/usr/bin/env python

"""
Uses pysam to convert a CRAM file to a sorted bam file.
usage: %prog in_file out_file
"""
import optparse
import os

from pysam import sort  # type: ignore[attr-defined]


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    input_fname, output_fname = args
    slots = os.getenv("GALAXY_SLOTS", 1)
    sort(f"-@{slots}", "-o", output_fname, "-O", "bam", "-T", ".", input_fname)


if __name__ == "__main__":
    main()
