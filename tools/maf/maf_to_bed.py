#!/usr/bin/env python

"""
Read a maf and output intervals for specified list of species.
"""
import sys, os, tempfile
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
        
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    #where to store files that become additional output
    database_tmp_dir = sys.argv[5]
    
    species = sys.argv[3].split(',')
    partial = sys.argv[4]
    out_files = {}
    primary_spec = None
    
    if "None" in species:
        species = {}
        try:
            for i, m in enumerate( maf.Reader( open( input_filename, 'r' ) ) ):
                for c in m.components:
                    spec,chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    species[spec] = ""
            species = species.keys()
        except:
            print >>sys.stderr, "Invalid MAF file specified"
            return
        
    if "?" in species:
        print >>sys.stderr, "Invalid dbkey specified"
        return
        
    
    for i in range( 0, len( species ) ):
        spec = species[i]
        if i == 0:
            out_files[spec] = open( output_filename, 'w' )
            primary_spec = spec
        else:
            out_files[spec] = tempfile.NamedTemporaryFile( mode = 'w', dir = database_tmp_dir, suffix = '.maf_to_bed' )
            filename = out_files[spec].name
            out_files[spec].close()
            out_files[spec] = open( filename, 'w' )
    num_species = len( species )
    
    print "Restricted to species:", ",".join( species )
    
    file_in = open( input_filename, 'r' )
    maf_reader = maf.Reader( file_in )
    
    block_num = -1
    
    for i, m in enumerate( maf_reader ):
        block_num += 1
        if "None" not in species:
            m = m.limit_to_species( species )
        l = m.components
        if len(l) < num_species and partial == "partial_disallowed": continue
        for c in l:
            spec,chrom = maf.src_split( c.src )
            if not spec or not chrom:
                    spec = chrom = c.src
            if spec not in out_files.keys():
                out_files[spec] = tempfile.NamedTemporaryFile( mode='w', dir = database_tmp_dir, suffix = '.maf_to_bed' )
                filename = out_files[spec].name
                out_files[spec].close()
                out_files[spec] = open( filename, 'w' )
            
            if c.strand == "-":
                out_files[spec].write( chrom + "\t" + str( c.src_size - c.end ) + "\t" + str( c.src_size - c.start ) + "\t" + spec + "_" + str( block_num ) + "\t" + "0\t" + c.strand + "\n" )
            else:
                out_files[spec].write( chrom + "\t" + str( c.start ) + "\t" + str( c.end ) + "\t" + spec + "_" + str( block_num ) + "\t" + "0\t" + c.strand + "\n" )
            
    file_in.close()
    for file_out in out_files.keys():
        out_files[file_out].close()

    for spec in out_files.keys():
        if spec != primary_spec:
            print "#FILE\t" + spec + "\t" + os.path.join( database_tmp_dir, os.path.split( out_files[spec].name )[1] )
        else:
            print "#FILE1\t" + spec + "\t" + out_files[spec].name

if __name__ == "__main__": __main__()
