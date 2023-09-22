#!/usr/bin/env python
# Variants of this code exists in 2 places, this file which has no
# user facing options which is called for implicit data conversion,
# lib/galaxy/datatypes/converters/fasta_to_tabular_converter.py
# and the user-facing Galaxy tool of the same name which has many
# options. That version is now on GitHub and the Galaxy Tool Shed:
# https://github.com/galaxyproject/tools-devteam/tree/master/tools/fasta_to_tabular
# https://toolshed.g2.bx.psu.edu/view/devteam/fasta_to_tabular
"""
Input: fasta
Output: tabular
"""
import os
import sys


def __main__():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    if not os.path.isfile(infile):
        sys.stderr.write(f"Input file {infile!r} not found\n")
        sys.exit(1)

    with open(infile) as inp:
        with open(outfile, "w") as out:
            sequence = ""
            for line in inp:
                line = line.rstrip("\r\n")
                if line.startswith(">"):
                    if sequence:
                        # Flush sequence from previous FASTA record,
                        # removing any white space
                        out.write("".join(sequence.split()) + "\n")
                        sequence = ""
                    # Strip off the leading '>' and remove any pre-existing
                    # tabs which would trigger extra columns; write with
                    # tab to separate this from the sequence column:
                    out.write(line[1:].replace("\t", " ") + "\t")
                else:
                    # Continuing sequence,
                    sequence += line
            # End of FASTA file, flush last sequence
            if sequence:
                out.write("".join(sequence.split()) + "\n")


if __name__ == "__main__":
    __main__()
