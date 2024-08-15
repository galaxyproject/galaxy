#!/usr/bin/env python
"""
Read a table dump in the UCSC gene table format and print a tab separated
list of intervals corresponding to requested features of each gene.

usage: ucsc_gene_table_to_intervals.py [options]

options:
  -h, --help                  show this help message and exit
  -rREGION, --region=REGION
                              Limit to region: one of coding, utr3, utr5, transcribed [default]
  -e, --exons                 Only print intervals overlapping an exon
  -i, --input=inputfile       input file
  -o, --output=outputfile     output file
"""
from __future__ import print_function

import optparse
import sys

assert sys.version_info[:2] >= (2, 6)


def main():
    parser = optparse.OptionParser(usage="%prog [options] ")
    parser.add_option("-s", "--strand", action="store_true", dest="strand", help="Print strand after interval")
    parser.add_option("-i", "--input", dest="input", default=None, help="Input file")
    parser.add_option("-o", "--output", dest="output", default=None, help="Output file")
    options, args = parser.parse_args()

    try:
        out_file = open(options.output, "w")
    except Exception:
        print("Bad output file.", file=sys.stderr)
        sys.exit(0)

    try:
        in_file = open(options.input)
    except Exception:
        print("Bad input file.", file=sys.stderr)
        sys.exit(0)

    # Read table and handle each gene
    for line in in_file:
        try:
            if line[0:1] == "#":
                continue

            # Parse fields from gene tabls
            fields = line.split("\t")
            chrom = fields[0]
            tx_start = int(fields[1])
            int(fields[2])
            name = fields[3]
            strand = fields[5].replace(" ", "_")
            int(fields[6])
            int(fields[7])

            exon_starts = [int(_) + tx_start for _ in fields[11].rstrip(",\n").split(",")]
            exon_ends = [int(_) for _ in fields[10].rstrip(",\n").split(",")]
            exon_ends = [x + y for x, y in zip(exon_starts, exon_ends)]

            i = 0
            while i < len(exon_starts) - 1:
                intron_starts = exon_ends[i] + 1
                intron_ends = exon_starts[i + 1] - 1
                if strand:
                    print_tab_sep(out_file, chrom, intron_starts, intron_ends, name, "0", strand)
                else:
                    print_tab_sep(out_file, chrom, intron_starts, intron_ends)
                i += 1
        except Exception:
            continue


def print_tab_sep(out_file, *args):
    """Print items in `l` to stdout separated by tabs"""
    print("\t".join(str(f) for f in args), file=out_file)


if __name__ == "__main__":
    main()
