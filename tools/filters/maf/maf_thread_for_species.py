#!/usr/bin/env python

"""
Read a maf file and write out a new maf with only blocks having all of
the passed in species, after dropping any other species and removing columns 
containing only gaps. This will attempt to fuse together any blocks
which are adjacent after the unwanted species have been dropped. 

usage: %prog input_maf output_maf species1,species2
"""

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

import bx.align.tools.thread
import bx.align.tools.fuse

def main():

    input_file = sys.argv.pop(1)
    output_file = sys.argv.pop(1)
    species = sys.argv.pop(1).split(',')

    
    try:
        maf_reader = bx.align.maf.Reader( open(input_file) )
    except:
        print sys.stderr, "Unable to open source MAF file"
        sys.exit()
    try:
        maf_writer = bx.align.tools.fuse.FusingAlignmentWriter( bx.align.maf.Writer( open(output_file, 'w') ) )
    except:
        print sys.stderr, "Unable to open output file"
        sys.exit()
    try:
        for m in maf_reader:            
            new_components = bx.align.tools.thread.get_components_for_species( m, species )
            if new_components: 
                bx.align.tools.thread.remove_all_gap_columns( new_components )
                m.components = new_components
                m.score = 0.0 
                maf_writer.write( m )
    except:
        print sys.stderr, "Error steping through MAF File"
        sys.exit()
    maf_reader.close()
    maf_writer.close()
    
if __name__ == "__main__": main()
