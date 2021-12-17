#!/usr/bin/env python
"""
Input: parquet
Output: csv
"""
import os
import sys
from pyarrow import csv
from pyarrow import parquet

def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)

    csv.write_csv(parquet.read_table(infile), outfile)

if __name__ == "__main__":
    __main__()
