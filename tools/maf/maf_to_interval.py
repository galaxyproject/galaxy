#!/usr/bin/env python

"""
Read a maf and output intervals for specified list of species.
"""
import os
import sys

from bx.align import maf

from galaxy.tools.util import maf_utilities


def __main__():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    output_id = sys.argv[3]
    # where to store files that become additional output
    database_tmp_dir = sys.argv[4]
    primary_spec = sys.argv[5]
    species = sys.argv[6].split( ',' )
    all_species = sys.argv[7].split( ',' )
    partial = sys.argv[8]
    keep_gaps = sys.argv[9]
    out_files = {}

    if "None" in species:
        species = []

    if primary_spec not in species:
        species.append( primary_spec )
    if primary_spec not in all_species:
        all_species.append( primary_spec )

    all_species.sort()
    for spec in species:
        if spec == primary_spec:
            out_files[ spec ] = open( output_filename, 'wb+' )
        else:
            out_files[ spec ] = open( os.path.join( database_tmp_dir, 'primary_%s_%s_visible_interval_%s' % ( output_id, spec, spec ) ), 'wb+' )
        out_files[ spec ].write( '#chrom\tstart\tend\tstrand\tscore\tname\t%s\n' % ( '\t'.join( all_species ) ) )
    num_species = len( all_species )

    file_in = open( input_filename, 'r' )
    maf_reader = maf.Reader( file_in )

    for i, m in enumerate( maf_reader ):
        for j, block in enumerate( maf_utilities.iter_blocks_split_by_species( m ) ):
            if len( block.components ) < num_species and partial == "partial_disallowed":
                continue
            sequences = {}
            for c in block.components:
                spec, chrom = maf_utilities.src_split( c.src )
                if keep_gaps == 'remove_gaps':
                    sequences[ spec ] = c.text.replace( '-', '' )
                else:
                    sequences[ spec ] = c.text
            sequences = '\t'.join( [ sequences.get( _, '' ) for _ in all_species ] )
            for spec in species:
                c = block.get_component_by_src_start( spec )
                if c is not None:
                    spec2, chrom = maf_utilities.src_split( c.src )
                    assert spec2 == spec, Exception( 'Species name inconsistancy found in component: %s != %s' % ( spec, spec2 ) )
                    out_files[ spec ].write( "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % ( chrom, c.forward_strand_start, c.forward_strand_end, c.strand, m.score, "%s_%s_%s" % (spec, i, j), sequences ) )
    file_in.close()
    for file_out in out_files.values():
        file_out.close()


if __name__ == "__main__":
    __main__()
