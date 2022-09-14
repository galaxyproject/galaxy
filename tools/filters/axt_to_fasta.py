#!/usr/bin/env python
"""
Adapted from bx/scripts/axt_to_fasta.py
"""
from __future__ import print_function

import sys

import bx.align.axt


def usage(s=None):
    message = """
axt_to_fasta species1 species2 < axt_file > fasta_file
"""
    if s is None:
        sys.exit(message)
    else:
        sys.exit("%s\n%s" % (s, message))


def main():
    # check the command line
    species1 = sys.argv[1]
    species2 = sys.argv[2]

    # convert the alignment blocks

    reader = bx.align.axt.Reader(sys.stdin, support_ids=True, species1=species1, species2=species2)

    for a in reader:
        if "id" in a.attributes:
            id = a.attributes["id"]
        else:
            id = None
        print_component_as_fasta(a.components[0], id)
        print_component_as_fasta(a.components[1], id)
        print()


# TODO: this should be moved to a bx.align.fasta module
def print_component_as_fasta(c, id=None):
    header = ">%s_%s_%s" % (c.src, c.start, c.start + c.size)
    if id is not None:
        header += " " + id
    print(header)
    print(c.text)


if __name__ == "__main__":
    main()
