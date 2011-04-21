#!/usr/bin/env python

"""
basic version
need to add
    o indexing
    o better error handing
"""

import sys
from optparse import OptionParser

def main_function(parse_arguments=None):
    if parse_arguments is None:
        parse_arguments = lambda arguments: (None, arguments)
    def main_decorator(to_decorate):
        def decorated_main(arguments=None):
            if arguments is None:
                arguments = sys.argv
            options, arguments = parse_arguments(arguments)
            sys.exit(to_decorate(options, arguments))
        return decorated_main
    return main_decorator

def parse_arguments(arguments):
    parser = OptionParser()
    parser.add_option('--input', dest='input')
    parser.add_option('--output', dest='output')
    parser.add_option('--chrlens_loc', dest='chrlens_loc')
    parser.add_option('--num_snps', dest='num_snps')
    parser.add_option('--ref_chrom_col', dest='ref_chrom_col')
    parser.add_option('--ref_pos_col', dest='ref_pos_col')
    parser.add_option('--species', dest='species')
    return parser.parse_args(arguments[1:])


@main_function(parse_arguments)
def main(options, arguments):
    ref_chrom_idx = int( options.ref_chrom_col ) - 1
    ref_pos_idx = int( options.ref_pos_col ) - 1

    chrlens_fh = open( options.chrlens_loc, 'r' )
    for line in chrlens_fh:
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            if len(elems) >= 2 and elems[0] == options.species:
                chrom_info_file = elems[1]

    chrom_info = open( chrom_info_file, 'r' )
    total_len = 0
    for i, line in enumerate( chrom_info ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            elems = line.split()
            if len(elems) == 2:
                chrom = elems[0]
                try:
                    chrom_len = int(elems[1])
                except ValueError:
                    sys.stderr.write( "bad chrom len in line %d column 2: %s\n" % ( i, elems[1] ) )
                    sys.exit(1)
                total_len += chrom_len;
    chrom_info.close()

    space = total_len / int( options.num_snps )
    out_fh = open( options.output, 'w')

    old_chrom = None
    next_print = 0
    for i, line in enumerate( open( options.input, 'r' ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            if len(elems) >= 2:
                chrom = elems[ref_chrom_idx]
                try:
                    pos = int(elems[ref_pos_idx])
                except ValueError:
                    sys.stderr.write( "bad reference position in line %d column %s: %s\n" % ( i, options.ref_pos_col, elems[ref_pos_idx] ) )
                    sys.exit(1)
                if chrom != old_chrom:
                    old_chrom = chrom
                    next_print = 0
                if pos >= next_print:
                    out_fh.write("%s\n" % (line))
                    next_print += space;

if __name__ == "__main__":
    main()


