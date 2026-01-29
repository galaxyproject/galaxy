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
    parser.add_option(
        "-r",
        "--region",
        dest="region",
        default="transcribed",
        help="Limit to region: one of coding, utr3, utr5, transcribed [default]",
    )
    parser.add_option(
        "-e", "--exons", action="store_true", dest="exons", help="Only print intervals overlapping an exon"
    )
    parser.add_option("-s", "--strand", action="store_true", dest="strand", help="Print strand after interval")
    parser.add_option("-i", "--input", dest="input", default=None, help="Input file")
    parser.add_option("-o", "--output", dest="output", default=None, help="Output file")
    options, args = parser.parse_args()
    assert options.region in ("coding", "utr3", "utr5", "transcribed"), "Invalid region argument"

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

    print("Region:", options.region + ";")
    print("Only overlap with Exons:", end=" ")
    if options.exons:
        print("Yes")
    else:
        print("No")

    # Read table and handle each gene
    for line in in_file:
        try:
            if line[0:1] == "#":
                continue
            # Parse fields from gene tabls
            fields = line.split("\t")
            name = fields[0]
            chrom = fields[1]
            strand = fields[2].replace(" ", "_")
            tx_start = int(fields[3])
            tx_end = int(fields[4])
            cds_start = int(fields[5])
            cds_end = int(fields[6])

            # Determine the subset of the transcribed region we are interested in
            if options.region == "utr3":
                if strand == "-":
                    region_start, region_end = tx_start, cds_start
                else:
                    region_start, region_end = cds_end, tx_end
            elif options.region == "utr5":
                if strand == "-":
                    region_start, region_end = cds_end, tx_end
                else:
                    region_start, region_end = tx_start, cds_start
            elif options.region == "coding":
                region_start, region_end = cds_start, cds_end
            else:
                region_start, region_end = tx_start, tx_end

            # If only interested in exons, print the portion of each exon overlapping
            # the region of interest, otherwise print the span of the region
            if options.exons:
                exon_starts = map(int, fields[8].rstrip(",\n").split(","))
                exon_ends = map(int, fields[9].rstrip(",\n").split(","))
                for start, end in zip(exon_starts, exon_ends):
                    start = max(start, region_start)
                    end = min(end, region_end)
                    if start < end:
                        if strand:
                            print_tab_sep(out_file, chrom, start, end, name, "0", strand)
                        else:
                            print_tab_sep(out_file, chrom, start, end)
            else:
                if strand:
                    print_tab_sep(out_file, chrom, region_start, region_end, name, "0", strand)
                else:
                    print_tab_sep(out_file, chrom, region_start, region_end)
        except Exception:
            continue


def print_tab_sep(out_file, *args):
    """Print items in `l` to stdout separated by tabs"""
    print("\t".join(str(f) for f in args), file=out_file)


if __name__ == "__main__":
    main()
