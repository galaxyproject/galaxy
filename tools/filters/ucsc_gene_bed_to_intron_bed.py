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

import optparse
import string
import sys

assert sys.version_info[:2] >= ( 2, 4 )


def main():
    parser = optparse.OptionParser( usage="%prog [options] " )
    parser.add_option( "-s", "--strand", action="store_true", dest="strand",
                       help="Print strand after interval" )
    parser.add_option( "-i", "--input", dest="input", default=None,
                       help="Input file" )
    parser.add_option( "-o", "--output", dest="output", default=None,
                       help="Output file" )
    options, args = parser.parse_args()

    try:
        out_file = open(options.output, "w")
    except:
        print >> sys.stderr, "Bad output file."
        sys.exit(0)

    try:
        in_file = open(options.input)
    except:
        print >> sys.stderr, "Bad input file."
        sys.exit(0)

    # Read table and handle each gene
    for line in in_file:
        try:
            if line[0:1] == "#":
                continue

            # Parse fields from gene tabls
            fields = line.split( '\t' )
            chrom = fields[0]
            tx_start = int( fields[1] )
            int( fields[2] )
            name = fields[3]
            strand = fields[5].replace(" ", "_")
            int( fields[6] )
            int( fields[7] )

            exon_starts = map( int, fields[11].rstrip( ',\n' ).split( ',' ) )
            exon_starts = map((lambda x: x + tx_start ), exon_starts)
            exon_ends = map( int, fields[10].rstrip( ',\n' ).split( ',' ) )
            exon_ends = map((lambda x, y: x + y ), exon_starts, exon_ends)

            i = 0
            while i < len(exon_starts) - 1:
                intron_starts = exon_ends[i] + 1
                intron_ends = exon_starts[i + 1] - 1
                if strand:
                    print_tab_sep(out_file, chrom, intron_starts, intron_ends, name, "0", strand )
                else:
                    print_tab_sep(out_file, chrom, intron_starts, intron_ends )
                i += 1
        except:
            continue


def print_tab_sep(out_file, *args ):
    """Print items in `l` to stdout separated by tabs"""
    print >>out_file, string.join( [ str( f ) for f in args ], '\t' )

if __name__ == "__main__":
    main()
