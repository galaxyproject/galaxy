#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file, concatenating blocks

usage %prog species1,species2 maf_file out_file
"""
#Dan Blankenberg
from __future__ import division

import textwrap
import sys
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

def __main__():
    print "Restricted to species:", sys.argv[1]
    
    texts = {}

    input_filename = sys.argv[2]
    output_filename = sys.argv[3]
    species = sys.argv[1].split( ',' )
    
    if "None" in species:
        species = get_species( input_filename )
    
    file_out = open( output_filename, 'w' )
    for spec in species:
        file_out.write( ">" + spec + "\n" )
        try:
            for m in maf.Reader( open( input_filename, 'r' ) ):
                c = m.get_component_by_src_start( spec ) 
                if c: file_out.write( c.text )
                else: file_out.write( "-" * m.text_size )
        except:
            print >>sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
        file_out.write( "\n" )
    file_out.close()

def get_species( maf_filename ):
        try:
            species={}
            
            file_in = open( maf_filename, 'r' )
            maf_reader = maf.Reader( file_in )
            
            for i, m in enumerate( maf_reader ):
                l = m.components
                for c in l:
                    spec, chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    species[spec] = spec
            
            file_in.close()
            
            species = species.keys()
            species.sort()
            return species
        except:
            return []

if __name__ == "__main__": __main__()
