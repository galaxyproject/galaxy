#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file.
"""
#Dan Blankenberg
import sys
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

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
                file_out.write( ">" + component.src + "(" + component.strand + "):" + str( component.start ) + "-" + str( component.end ) + "|" + spec + "_" + str( block_num ) + "\n" )
                file_out.write( component.text + "\n" )
            file_out.write( "\n" )
        file_in.close()
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    file_out.close()

if __name__ == "__main__": __main__()
