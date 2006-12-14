#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file, concatenating blocks

usage %prog species1,species2 maf_file out_file
"""

from __future__ import division

import textwrap
import sys
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

def __main__():
    print "Restricted to species:",sys.argv[1]
    
    texts = {}

    input_filename = sys.argv[2]
    output_filename = sys.argv[3]
    species = sys.argv[1].split(',')
    
    if "None" in species:
        species = get_species(input_filename)
    
    file_in = open(input_filename, 'r')
    file_out = open(output_filename, 'w')

    for s in species: texts[s] = []
    maf_reader = maf.Reader( file_in )
    for m in maf_reader:
        for s in species:
            c = m.get_component_by_src_start( s ) 
            if c: texts[s].append( c.text )
            else: texts[s].append( "-" * m.text_size )
    for s in species:
        file_out.write(">"+s+"\n")
        file_out.write("".join(texts[s])+"\n")
    
    file_in.close()
    file_out.close()
    
    
def print_n( s, n, f = sys.stdout ):
    p = 0
    while p < len( s ):
        print >> f, s[p:min(p+n,len(s))]
        p += n

def get_species(maf_filename):
        try:
            species={}
            
            file_in = open(maf_filename, 'r')
            maf_reader = maf.Reader( file_in )
            
            for i, m in enumerate( maf_reader ):
                l = m.components
                for c in l:
                    spec,chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    species[spec]=spec
            
            file_in.close()
            
            species = species.keys()
            species.sort()
            return species
        except:
            return []


if __name__ == "__main__": __main__()
