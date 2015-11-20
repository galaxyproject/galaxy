#!/usr/bin/env python

"""
Uses bcftools to extract a bcf from a bcf.gz

usage: %prog in_file out_file
"""
import optparse
import subprocess


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    input_fname, output_fname = args

    subprocess.call(["bcftools", "view", input_fname, "-o", output_fname, "-O", "u"])


if __name__ == "__main__":
    main()
