#!/usr/bin/env python

"""
Calculate coverage of one query on another, and append the coverage to
the last two columns as bases covered and percent coverage.

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for start, end, strand in first file
    -2, --cols2=N,N,N,N: Columns for start, end, strand in second file
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys, tempfile
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.merge import *
from bx.cookbook import doc_optparse

from galaxyops import *

def main():

    upstream_pad = 0
    downstream_pad = 0

    options, args = doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        chr_col_2, start_col_2, end_col_2, strand_col_2 = parse_cols_arg( options.cols2 )      
        in_fname, in2_fname, out_fname = args
    except:
        print >> sys.stderr, "Data issue: Please check the metadata attributes of the chosen input by clicking on the pencil icon next to it."
        sys.exit()

    try:
        out_file = open( out_fname, "w" )
    except:
        print >> sys.stderr, "Unable to open output file"
        sys.exit()
        
    chr_list = []
    start_list = []
    end_list = []
    for line in open(in2_fname, 'r'):
        line = line.rstrip("\r\n")
        if not(line) or line == "" or line[0:1] == '#':
            continue
        elems = line.split('\t')
        chr_list.append(elems[chr_col_2])
        start_list.append(elems[start_col_2])
        end_list.append(elems[end_col_2])

    for line1 in open(in_fname, 'r'):
        fp = 0 #number of features fully present
        fp_p = 0 #% covered by fp features
        pp = 0 #number of overlapping features
        pp_p = 0 #% covered by pp features
        pp_l = 0 #partly present on left side of the window
        pp_l_p = 0 #% covered by pp_l features
        pp_r = 0 #partly present on right side of the window
        pp_r_p = 0 #% covered by pp_r features
        np = 0 #number of features present
        chr1 = line1.split('\t')[chr_col_1]
        start1 = int(line1.split('\t')[start_col_1])
        end1 = int(line1.split('\t')[end_col_1])
        if not(chr1 in chr_list):
            continue
        
        tmpfile1 = tempfile.NamedTemporaryFile()
        tmpfile2 = tempfile.NamedTemporaryFile()
        
        for i, chr2 in enumerate(chr_list):
            start2 = int(start_list[i])
            end2 = int(end_list[i])
            if chr2 == chr1:
                if (start2 < start1 and end2 < start1) or (start2 >end1 and end2 >end1):
                    continue
                if start2 in range(start1,end1) and end2 in range(start1,end1):    #feature completely lies in the window
                    fp += 1
                    print >>tmpfile1, chr2 + '\t' + str(start2) + '\t' + str(end2)
                elif (start2 not in range(start1,end1)) and (end2 not in range(start1,end1)):    #feature is longer than the window and covers the window completely                        #feature overlaps  the right side of the window
                    if (start1 in range(start2,end2)) and (end1 in range(start2,end2)):
                        fp += 1
                        fp_p += 100.00
                elif (start2 not in range(start1,end1)) or (end2 not in range(start1,end1)):    #feature partially overlaps with the window
                    pp += 1
                    print >>tmpfile2, chr2 + '\t' + str(start2) + '\t' + str(end2)
                    
        g1 = NiceReaderWrapper( open(tmpfile1.name, 'r' ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col = strand_col_2,
                            fix_strand=True)
        g2 = NiceReaderWrapper( open(tmpfile2.name, 'r' ),
                            chrom_col=chr_col_2,
                            start_col=start_col_2,
                            end_col=end_col_2,
                            strand_col = strand_col_2,
                            fix_strand=True)
        
        tmpfile1.readline()
        tmpfile2.readline()
        mincols = 1
        #merge over-lapping features before computing their coverage
        #g1 has features completely present in the window
        for line in merge(g1,mincols=mincols):
            if type( line ) is GenomicInterval:
                start = int(line.startCol)
                end = int(line.endCol)
            elif type( line ) is list:
                start = int(line[start_col_1])
                end = int(line[end_col_1])
            fp_p += (100.0*abs(end - start)/abs(end1-start1))
        
        #g2 has features ovelapping either ends of the window
        for line in merge(g2,mincols=mincols):
            if type( line ) is GenomicInterval:
                start = int(line.startCol)
                end = int(line.endCol)
            elif type( line ) is list:
                start = int(line[start_col_1])
                end = int(line[end_col_1])
            if start in range(start1,end1) and end not in range(start1,end1):
                pp_p += (100.0*abs(end1 - start)/abs(end1-start1))
            elif start not in range(start1,end1) and end in range(start1,end1):
                pp_p += (100.0*abs(end - start1)/abs(end1-start1))
        
        print >>out_file, "%s\t%d\t%2.2f\t%d\t%2.2f" %(line1.strip(),fp,fp_p,pp,pp_p) 
        
if __name__ == "__main__":
    main()
