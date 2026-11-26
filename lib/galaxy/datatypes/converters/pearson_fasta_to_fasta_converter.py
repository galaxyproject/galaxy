#!/usr/bin/env python
"""
Input: pearson_fasta
Output: fasta

Drops the lines before the first '>' header (the ';' comment block) and copies
everything from that header on unchanged.
"""

import shutil
import sys


def __main__() -> None:
    infile = sys.argv[1]
    outfile = sys.argv[2]

    with open(infile, "rb") as inp:
        for line in inp:
            if line.startswith(b">"):
                break
        else:
            sys.exit(f"No FASTA header ('>') found in {infile!r}")
        with open(outfile, "wb") as out:
            out.write(line)
            shutil.copyfileobj(inp, out)


if __name__ == "__main__":
    __main__()
