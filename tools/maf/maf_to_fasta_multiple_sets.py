#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file.
"""
#Dan Blankenberg
import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
from galaxy.tools.util import maf_utilities

def __main__():
    print "Restricted to species:", sys.argv[3]
    
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    species = sys.argv[3].split( ',' )
    partial = sys.argv[4]
    num_species = len( species )
    
    file_in = open( input_filename, 'r' )
    try:
        maf_reader = maf.Reader( file_in )
        
        file_out = open( output_filename, 'w' )
        
        for block_num, block in enumerate( maf_reader ):
            if "None" not in species:
                block = block.limit_to_species( species )
            if len( block.components ) < num_species and partial == "partial_disallowed": continue
            for component in block.components:
                spec, chrom = maf.src_split( component.src )
                if not spec or not chrom:
                        spec = chrom = component.src
                file_out.write( "%s\n" % maf_utilities.get_fasta_header( component, suffix = "%s_%i" % ( spec, block_num ) ) )
                file_out.write( "%s\n" % component.text )
            file_out.write( "\n" )
        file_in.close()
    except Exception, e:
        print >>sys.stderr, "Your MAF file appears to be malformed:", e
        sys.exit()
    file_out.close()

if __name__ == "__main__": __main__()
