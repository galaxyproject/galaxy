#!/usr/bin/python2.4

"""
Estimate INDEL rates.

usage: %prog maf_input out_file1 out_file2
"""

from __future__ import division
import pkg_resources 
pkg_resources.require( "bx-python" )
pkg_resources.require( "lrucache" )
try:
    pkg_resources.require("numpy")
    pkg_resources.require( "python-lzo" )
except:
    pass

import psyco_full
import sys
import os, os.path
from UserDict import DictMixin
import bx.wiggle
from bx.binned_array import BinnedArray, FileBinnedArray
from bx.bitset import *
from bx.bitset_builders import *
from fpconst import isNaN
from bx.cookbook import doc_optparse
from galaxy.tools.exception_handling import *
import bx.align.maf

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        #chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols )
        inp_file, out_file1 = args    
    except:
        doc_optparse.exception()
    
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
    
    print >>fout1, "#Block\tSource\tStart\tEnd\tEvent"
    for block_ind, block in enumerate(maf_reader):
        if len(block.components) != 2:
            continue
        seqs = []
        srcs = []
        starts = []
        gaplens = []
        gapstatus = []
        starts.append(block.components[0].start)
        for seq_num in range(len(block.components)):
            seqs.append(block.components[seq_num].text)
            srcs.append(block.components[seq_num].src)
            starts.append(block.components[seq_num].start)
            gaplens.append(0)
            gapstatus.append(0)

        pos = 0        #character column position
        nt_pos1 = 0    #nt positions
        nt_pos2 = 0
        while pos < len(seqs[0]):
            for j,elem in enumerate(seqs):
                if gapstatus[j] == 0:
                    gaplens[j] = 0
            if seqs[0][pos] == '-':
                next = pos+1
                leng = 1
                while next < len(seqs[0]):
                    if seqs[0][next] == '-':
                        leng += 1
                    
                if seq2[pos] != '-':
                    nt_pos2 += 1
                    gaplen1 += 1
                    prev_pos_gap1 = 1
                    #write 2
                    if prev_pos_gap2 == 1:
                        prev_pos_gap2 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos2-1,nt_pos2,gaplen2)
                    if pos == len(seq1)-1:
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1,nt_pos1+1,gaplen1)
                else:
                    if prev_pos_gap1 == 1:
                        prev_pos_gap1 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,gaplen1)
                    elif prev_pos_gap2 == 1:
                        prev_pos_gap2 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos2-1,nt_pos2,gaplen2)
            else:
                nt_pos1 += 1
                if seq2[pos] != '-':
                    nt_pos2 += 1
                    #write both
                    if prev_pos_gap1 == 1:
                        prev_pos_gap1 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,gaplen1)
                    elif prev_pos_gap2 == 1:
                        prev_pos_gap2 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos2-1,nt_pos2,gaplen2)
                else:
                    gaplen2 += 1
                    prev_pos_gap2 = 1
                    #write 1
                    if prev_pos_gap1 == 1:
                        prev_pos_gap1 = 0
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src1,nt_pos1-1,nt_pos1,gaplen1)
                    if pos == len(seq1)-1:
                        print >>fout1,"%d\t%s\t%s\t%s\t%s" %(block_ind+1,src2,nt_pos2,nt_pos2+1,gaplen2)
            pos += 1
if __name__ == "__main__":
    main()