#!/usr/bin/env python

"""
Estimate INDELs for pair-wise alignments.

usage: %prog maf_input out_file1 out_file2
"""

from __future__ import division
from galaxy import eggs
import pkg_resources 
pkg_resources.require( "bx-python" )
try:
    pkg_resources.require("numpy")
except:
    pass
import psyco_full
import sys
from bx.cookbook import doc_optparse
from galaxy.tools.exception_handling import *
import bx.align.maf

assert sys.version_info[:2] >= ( 2, 4 )

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        inp_file, out_file1 = args    
    except:
        print >> sys.stderr, "Tool initialization error."
        sys.exit()
    
    try:
        fin = open(inp_file,'r')
    except:
        print >> sys.stderr, "Unable to open input file"
        sys.exit()
    try:
        fout1 = open(out_file1,'w')
        #fout2 = open(out_file2,'w')
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()

    try:
        maf_reader = bx.align.maf.Reader( open(inp_file, 'r') )
    except:
        print >>sys.stderr, "Your MAF file appears to be malformed."
        sys.exit()
    maf_count = 0
    
    print >>fout1, "#Block\tSource\tSeq1_Start\tSeq1_End\tSeq2_Start\tSeq2_End\tIndel_length"
    for block_ind, block in enumerate(maf_reader):
        if len(block.components) < 2:
            continue
        seq1 = block.components[0].text
        src1 = block.components[0].src
        start1 = block.components[0].start
        if len(block.components) == 2:
            seq2 = block.components[1].text
            src2 = block.components[1].src
            start2 = block.components[1].start
            #for pos in range(len(seq1)):
            nt_pos1 = start1-1    #position of the nucleotide (without counting gaps)
            nt_pos2 = start2-1
            pos = 0        #character column position
            gaplen1 = 0
            gaplen2 = 0
            prev_pos_gap1 = 0
            prev_pos_gap2 = 0
            while pos < len(seq1):
                if prev_pos_gap1 == 0:
                    gaplen1 = 0
                if prev_pos_gap2 == 0:
                    gaplen2 = 0
                    
                if seq1[pos] == '-':
                    if seq2[pos] != '-':
                        nt_pos2 += 1
                        gaplen1 += 1
                        prev_pos_gap1 = 1
                        #write 2
                        if prev_pos_gap2 == 1:
                            prev_pos_gap2 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos1,nt_pos1+1,nt_pos2-1,nt_pos2-1+gaplen2,gaplen2)
                        if pos == len(seq1)-1:
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1,nt_pos1+1,nt_pos2+1-gaplen1,nt_pos2+1,gaplen1)
                    else:
                        prev_pos_gap1 = 0
                        prev_pos_gap2 = 0
                        """
                        if prev_pos_gap1 == 1:
                            prev_pos_gap1 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,gaplen1)
                        elif prev_pos_gap2 == 1:
                            prev_pos_gap2 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos2-1,nt_pos2,gaplen2)
                        """
                else:
                    nt_pos1 += 1
                    if seq2[pos] != '-':
                        nt_pos2 += 1
                        #write both
                        if prev_pos_gap1 == 1:
                            prev_pos_gap1 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,nt_pos2-gaplen1,nt_pos2,gaplen1)
                        elif prev_pos_gap2 == 1:
                            prev_pos_gap2 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos1-gaplen2,nt_pos1,nt_pos2-1,nt_pos2,gaplen2)
                    else:
                        gaplen2 += 1
                        prev_pos_gap2 = 1
                        #write 1
                        if prev_pos_gap1 == 1:
                            prev_pos_gap1 = 0
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,nt_pos2,nt_pos2+gaplen1,gaplen1)
                        if pos == len(seq1)-1:
                            print >>fout1,"%d\t%s\t%s\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos1+1-gaplen2,nt_pos1+1,nt_pos2,nt_pos2+1,gaplen2)
                pos += 1
if __name__ == "__main__":
    main()
