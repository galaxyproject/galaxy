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
    parser.add_option('--primers_loc',
                        type='string', dest='primers_loc',
                        help='primers .loc file')
    parser.add_option('--scaffold_col',
                        type="int", dest='scaffold_col',
                        help='scaffold column in the input file')
    parser.add_option('--pos_col',
                        type="int", dest='pos_col',
                        help='position column in the input file')
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
    if not options.primers_loc:
        raise RuntimeError( 'missing --primers_loc option' )
    if not options.scaffold_col:
        raise RuntimeError( 'missing --scaffold_col option' )
    if not options.pos_col:
        raise RuntimeError( 'missing --pos_col option' )
    if not options.species:
        raise RuntimeError( 'missing --species option' )
    
    snps = gd.SnpFile( filename=options.input, seq_col=int( options.scaffold_col ), pos_col=int( options.pos_col ) )

    out_fh = gd._openfile( options.output, 'w' )

    primer_data_file = gd.get_filename_from_loc( options.species, options.primers_loc )
    file_root, file_ext = os.path.splitext( primer_data_file )
    primer_index_file = file_root + ".cdb"
    primers = gd.PrimersFile( data_file=primer_data_file, index_file=primer_index_file )

    while snps.next():
        seq, pos = snps.get_seq_pos()
        primer = primers.get_entry( seq, pos )
        if primer:
            out_fh.write( primer )

    out_fh.close()

if __name__ == "__main__":
    main()

