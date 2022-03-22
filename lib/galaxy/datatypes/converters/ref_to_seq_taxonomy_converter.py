#!/usr/bin/env python
"""
convert a ref.taxonomy file to a seq.taxonomy file
Usage:
%python ref_to_seq_taxonomy_converter.py <ref.taxonom> <seq.taxonomy>
"""
import re
import sys

assert sys.version_info[:2] >= (2, 4)


def __main__():
    with open(sys.argv[1]) as infile, open(sys.argv[2], "w") as outfile:
        for line in infile:
            line = line.rstrip()
            if line and not line.startswith("#"):
                fields = line.split("\t")
                # make sure the 2nd field (taxonomy) ends with a ;
                outfile.write(f"{fields[0]}\t{re.sub(';$', '', fields[1])};\n")


if __name__ == "__main__":
    __main__()
