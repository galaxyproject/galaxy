#!/usr/bin/env python
"""
Input: parquet
Output: csv
"""

import os
import sys

try:
    import pyarrow.csv as csv
    import pyarrow.parquet as parquet
except ImportError:
    csv = None
    parquet = None


def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)

    if csv is None or parquet is None:
        raise Exception("Cannot run conversion, pyarrow is not installed.")

    csv.write_csv(parquet.read_table(infile), outfile)


if __name__ == "__main__":
    __main__()
