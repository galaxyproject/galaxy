#!/usr/bin/env python2.5

import os
import sys
from optparse import OptionParser
import genome_diversity as gd

def main_function( parse_arguments=None ):
    if parse_arguments is None:
        parse_arguments = lambda arguments: ( None, arguments )
    def main_decorator( to_decorate ):
        def decorated_main( arguments=None ):
            if arguments is None:
                arguments = sys.argv
            options, arguments = parse_arguments( arguments )
            rc = 1
            try:
                rc = to_decorate( options, arguments )
            except Exception, err:
                sys.stderr.write( 'ERROR: %s\n' % str( err ) )
                traceback.print_exc()
            finally:
                sys.exit( rc )
        return decorated_main
    return main_decorator

def parse_arguments( arguments ):
    parser = OptionParser()
    parser.add_option('--input',
                        type='string', dest='input',
                        help='file of selected SNPs')
    parser.add_option('--output',
                        type='string', dest='output',
                        help='output file')
    parser.add_option('--snps_loc',
                        type='string', dest='snps_loc',
                        help='snps .loc file')
    parser.add_option('--scaffold_col',
                        type="int", dest='scaffold_col',
                        help='scaffold column in the input file')
    parser.add_option('--pos_col',
                        type="int", dest='pos_col',
                        help='position column in the input file')
    parser.add_option('--output_format',
                        type="string", dest='output_format',
                        help='output format, fasta or primer3')
    parser.add_option('--species',
                        type="string", dest='species',
                        help='species')
    return parser.parse_args( arguments[1:] )


@main_function( parse_arguments )
def main( options, arguments ):
    if not options.input:
        raise RuntimeError( 'missing --input option' )
    if not options.output:
        raise RuntimeError( 'missing --output option' )
    if not options.snps_loc:
        raise RuntimeError( 'missing --snps_loc option' )
    if not options.scaffold_col:
        raise RuntimeError( 'missing --scaffold_col option' )
    if not options.pos_col:
        raise RuntimeError( 'missing --pos_col option' )
    if not options.output_format:
        raise RuntimeError( 'missing --output_format option' )
    if not options.species:
        raise RuntimeError( 'missing --species option' )
    
    snps = gd.SnpFile( filename=options.input, seq_col=int( options.scaffold_col ), pos_col=int( options.pos_col ) )

    out_fh = gd._openfile( options.output, 'w' )

    snpcalls_file = gd.get_filename_from_loc( options.species, options.snps_loc )
    file_root, file_ext = os.path.splitext( snpcalls_file )
    snpcalls_index_file = file_root + ".cdb"
    snpcalls = gd.SnpcallsFile( data_file=snpcalls_file, index_file=snpcalls_index_file )

    while snps.next():
        seq, pos = snps.get_seq_pos()
        flanking_dna = snpcalls.get_flanking_dna( sequence=seq, position=pos, format=options.output_format )
        if flanking_dna:
            out_fh.write( flanking_dna )

    out_fh.close()

if __name__ == "__main__":
    main()

