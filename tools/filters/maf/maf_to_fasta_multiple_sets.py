#!/usr/bin/env python2.3

"""
Read a maf and print the text as a fasta file.
"""

from __future__ import division

import textwrap
import sys
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf

def __main__():
    print "Restricted to species:",sys.argv[3]
        
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    species = sys.argv[3].split(',')
    partial = sys.argv[4]
    num_species = len(species)
    
    file_in = open(input_filename, 'r')
    try:
        maf_reader = maf.Reader( file_in )
        
        file_out = open(output_filename, 'w')
        
        block_num=-1
        
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
                file_out.write(">"+c.src+"("+c.strand+"):"+str(c.start)+"-"+str(c.end)+"|"+spec+"_"+str(block_num)+"\n")
                file_out.write(c.text+"\n")
            file_out.write("\n")
        file_in.close()
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    file_out.close()

def print_n( s, n, f = sys.stdout ):
    p = 0
    while p < len( s ):
        print >> f, s[p:min(p+n,len(s))]
        p += n

if __name__ == "__main__": __main__()
