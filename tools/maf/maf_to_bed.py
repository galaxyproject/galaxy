#!/usr/bin/env python
"""
Read a maf and output intervals for specified list of species.
"""
from __future__ import print_function

import os
import sys

from bx.align import maf


def __main__():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    # where to store files that become additional output
    database_tmp_dir = sys.argv[5]

    species = sys.argv[3].split(',')
    partial = sys.argv[4]
    output_id = sys.argv[6]
    out_files = {}
    primary_spec = None

    if "None" in species:
        species = set()
        try:
            for i, m in enumerate( maf.Reader( open( input_filename, 'r' ) ) ):
                for c in m.components:
                    spec, chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    species.add(spec)
        except:
            print("Invalid MAF file specified", file=sys.stderr)
            return

    if "?" in species:
        print("Invalid dbkey specified", file=sys.stderr)
        return

    for i, spec in enumerate( species ):
        if i == 0:
            out_files[spec] = open( output_filename, 'w' )
            primary_spec = spec
        else:
            out_files[ spec ] = open( os.path.join( database_tmp_dir, 'primary_%s_%s_visible_bed_%s' % ( output_id, spec, spec ) ), 'wb+' )
    num_species = len( species )

    print("Restricted to species:", ",".join( species ))

    file_in = open( input_filename, 'r' )
    maf_reader = maf.Reader( file_in )

    block_num = -1

    for i, m in enumerate( maf_reader ):
        block_num += 1
        if "None" not in species:
            m = m.limit_to_species( species )
        l = m.components
        if len(l) < num_species and partial == "partial_disallowed":
            continue
        for c in l:
            spec, chrom = maf.src_split( c.src )
            if not spec or not chrom:
                    spec = chrom = c.src
            if spec not in out_files.keys():
                out_files[ spec ] = open( os.path.join( database_tmp_dir, 'primary_%s_%s_visible_bed_%s' % ( output_id, spec, spec ) ), 'wb+' )

            if c.strand == "-":
                out_files[spec].write( chrom + "\t" + str( c.src_size - c.end ) + "\t" + str( c.src_size - c.start ) + "\t" + spec + "_" + str( block_num ) + "\t" + "0\t" + c.strand + "\n" )
            else:
                out_files[spec].write( chrom + "\t" + str( c.start ) + "\t" + str( c.end ) + "\t" + spec + "_" + str( block_num ) + "\t" + "0\t" + c.strand + "\n" )

    file_in.close()
    for file_out in out_files.keys():
        out_files[file_out].close()

    print("#FILE1_DBKEY\t%s" % ( primary_spec ))


if __name__ == "__main__":
    __main__()
