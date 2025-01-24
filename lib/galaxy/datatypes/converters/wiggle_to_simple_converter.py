#!/usr/bin/env python
# code is same as ~/tools/stats/wiggle_to_simple.py
"""
Read a wiggle track and print out a series of lines containing
"chrom position score". Ignores track lines, handles bed, variableStep
and fixedStep wiggle lines.
"""

import sys

import bx.wiggle

from galaxy.util.ucsc import (
    UCSCLimitException,
    UCSCOutWrapper,
)


def main():
    with open(sys.argv[1]) as in_file, open(sys.argv[2], "w") as out_file:
        try:
            for fields in bx.wiggle.IntervalReader(UCSCOutWrapper(in_file)):
                out_file.write("{}\n".format("\t".join(map(str, fields))))
        except UCSCLimitException:
            # Wiggle data was truncated, at the very least need to warn the user.
            sys.stderr.write(
                'Encountered message from UCSC: "Reached output limit of 100000 data values", so be aware your data was truncated.'
            )


if __name__ == "__main__":
    main()
