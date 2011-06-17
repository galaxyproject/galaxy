#!/usr/bin/env python

import sys
import math
from optparse import OptionParser
import genome_diversity as gd

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

    ref_chrom_idx = to_int( options.ref_chrom_col ) -1
    ref_pos_idx = to_int( options.ref_pos_col ) -1

    if (ref_chrom_idx < 1) or (ref_pos_idx < 1) or (ref_chrom_idx == ref_pos_idx):
        print >> sys.stderr, "Cannot locate reference genome sequence (ref) or reference genome position (rPos) column for this dataset."
        sys.exit(1)

    chrlens = gd.ChrLens( options.chrlens_loc, options.species )

    total_len = 0
    for chrom in chrlens:
        total_len += chrlens.length(chrom)

    total_requested = int( options.num_snps )
    lines, data, comments = get_snp_lines_data_and_comments( options.input, ref_chrom_idx, ref_pos_idx )
    selected = select_snps( data, total_len, total_requested )
    out_data = fix_selection_and_order_like_input(data, selected, total_requested)
    write_selected_snps( options.output, out_data, lines, comments )

def to_int( value ):
    try:
        int_value = int( value )
    except ValueError:
        int_value = 0
    return int_value

def get_snp_lines_data_and_comments( filename, chrom_idx, pos_idx ):
    fh = open( filename, 'r' )
    if (chrom_idx >= pos_idx):
        needed = chrom_idx + 1
    else:
        needed = pos_idx + 1
    lines = []
    data = []
    comments = []
    line_idx = 0
    line_num = 0
    for line in fh:
        line_num += 1
        line = line.rstrip('\r\n')
        if line:
            if line.startswith('#'):
                comments.append(line)
            else:
                elems = line.split('\t')
                if len(elems) >= needed:
                    chrom = elems[chrom_idx]
                    try:
                        pos = int(elems[pos_idx])
                    except ValueError:
                        sys.stderr.write( "bad reference position in line %d column %d: %s\n" % ( line_num, pos_idx+1, elems[pos_idx] ) )
                        sys.exit(1)
                    lines.append(line)
                    chrom_sort = chrom.lstrip('chr')
                    data.append( [chrom_sort, chrom, pos, line_num, line_idx] )
                    line_idx += 1
    fh.close()
    data = sorted( data, key=lambda x: (x[0], x[2]) )
    return lines, data, comments

def select_snps( data, total_len, requested ):
    old_chrom = None
    next_print = 0
    selected = []
    space = total_len / requested
    for data_idx, datum in enumerate( data ):
        chrom = datum[1]
        pos = datum[2]
        if chrom != old_chrom:
            old_chrom = chrom
            next_print = 0
        if pos >= next_print:
            selected.append(data_idx)
            next_print += space
    return selected

def fix_selection_and_order_like_input(data, selected, requested):
    total_selected = len( selected )
    a = float( total_selected ) / requested
    b = a / 2

    idx_list = []
    for i in range( requested ):
        idx = int( math.ceil( i * a + b ) - 1 )
        idx_list.append( idx )

    out_data = []

    for i, data_idx in enumerate(selected):
        if total_selected > requested:
            if i in idx_list:
                out_data.append(data[data_idx])
        else:
            out_data.append(data[data_idx])

    out_data = sorted( out_data, key=lambda x: x[3] )

    return out_data

def write_selected_snps( filename, data, lines, comments ):
    fh = open( filename, 'w' )

    for comment in comments:
        fh.write("%s\n" % comment )

    for datum in data:
        line_idx = datum[4]
        fh.write("%s\n" % lines[line_idx])

    fh.close()

if __name__ == "__main__":
    main()


