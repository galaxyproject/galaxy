#!/usr/bin/env python

"""
Read a maf file and write out a new maf with only blocks having all of
the passed in species, after dropping any other species and removing columns 
containing only gaps. This will attempt to fuse together any blocks
which are adjacent after the unwanted species have been dropped. 

usage: %prog input_maf output_maf species1,species2
"""
#Dan Blankenberg
import sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

from bx.align.tools.thread import *
from bx.align.tools.fuse import *

def main():
    input_file = sys.argv.pop( 1 )
    output_file = sys.argv.pop( 1 )
    species = sys.argv.pop( 1 ).split( ',' )
    
    try:
        maf_reader = bx.align.maf.Reader( open( input_file ) )
    except:
        print >> sys.stderr, "Unable to open source MAF file"
        sys.exit()
    try:
        maf_writer = FusingAlignmentWriter( bx.align.maf.Writer( open( output_file, 'w' ) ) )
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()
    try:
        for m in maf_reader:            
            new_components = m.components
            if species != ['None']:
                new_components = get_components_for_species( m, species )
            if new_components: 
                remove_all_gap_columns( new_components )
                m.components = new_components
                m.score = 0.0 
                maf_writer.write( m )
    except Exception, e:
        print >> sys.stderr, "Error steping through MAF File: %s" % e
        sys.exit()
    maf_reader.close()
    maf_writer.close()
    
    print "Restricted to species: %s." % ", ".join( species )
    
if __name__ == "__main__": main()
