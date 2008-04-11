#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file, concatenating blocks

usage %prog species1,species2 maf_file out_file
"""
#Dan Blankenberg
import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
from galaxy.tools.util import maf_utilities

def __main__():
    print "Restricted to species:", sys.argv[1]
    
    texts = {}
    
    input_filename = sys.argv[2]
    output_filename = sys.argv[3]
    species = sys.argv[1].split( ',' )
    
    if "None" in species:
        species = maf_utilities.get_species_in_maf( input_filename )
    
    file_out = open( output_filename, 'w' )
    for spec in species:
        file_out.write( ">" + spec + "\n" )
        try:
            for block in maf.Reader( open( input_filename, 'r' ) ):
                component = block.get_component_by_src_start( spec )
                if component: file_out.write( component.text )
                else: file_out.write( "-" * block.text_size )
        except:
            print >>sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
        file_out.write( "\n" )
    file_out.close()


if __name__ == "__main__": __main__()
