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

import sys
import traceback
import fileinput
from warnings import warn

#from bx.intervals import *
from bx.intervals.io import *
#from bx.intervals.operations.coverage import *
from bx.cookbook import doc_optparse
from featureCounter_code import *

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
        doc_optparse.exception()

    g1 = NiceReaderWrapper( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1,
                                fix_strand=True)
    g2 = NiceReaderWrapper( fileinput.FileInput( in2_fname ),
                                chrom_col=chr_col_2,
                                start_col=start_col_2,
                                end_col=end_col_2,
                                strand_col=strand_col_2,
                                fix_strand=True)
    out_file = open( out_fname, "w" )

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
        fp_p = [] #% covered by fp features
        pp_l = 0 #partly present on left side of the window
        pp_l_p = [] #% covered by pp_l features
        pp_r = 0 #partly present on right side of the window
        pp_r_p = [] #% covered by pp_r features
        np = 0 #number of features present
        chr1 = line1.split('\t')[chr_col_1]
        start1 = int(line1.split('\t')[start_col_1])
        end1 = int(line1.split('\t')[end_col_1])
        if not(chr1 in chr_list):
            continue
        for i, chr2 in enumerate(chr_list):
            #chr2 = line2.split('\t')[chr_col_2]
            #start2 = int(line2.split('\t')[start_col_2])
            #end2 = int(line2.split('\t')[end_col_2])
            start2 = int(start_list[i])
            end2 = int(end_list[i])
            if chr2 == chr1:
                """
                if end2 < start2:
                    tmp = start2
                    start2 = end2
                    end2 = tmp
                """
                if (start2 < start1 and end2 < start1) or (start2 >end1 and end2 >end1):
                    continue
                if start2 in range(start1,end1):
                    if end2 in range(start1,end1):
                        fp+=1
                        fp_p.append("%2.2f"%(100.0*abs(end2 - start2)/abs(end1-start1)))
                    else:
                        pp_r = pp_r + (1.0*abs(end1 - start2)/abs(end2-start2))
                        pp_r_p.append("%2.2f"%(100.0*abs(end1 - start2)/abs(end1-start1)))
                        #pp_r_p = pp_r_p + abs(end1 - start2)
                elif end2 in range(start1,end1):
                    pp_l = pp_l + (1.0*abs(end2 - start1)/abs(end2 - start2)) 
                    pp_l_p.append("%2.2f"%(100.0*abs(end2 - start1)/abs(end1-start1)))
                    #pp_l_p = pp_l_p + abs(end2 - start1)
                else:
                    if (start1 in range(start2,end2)) and (end1 in range(start2,end2)):
                        fp = fp + (1.0*abs(end1 - start1)/abs(end2 - start2)) 
                        fp_p.append('100.00')
                        
        print >>out_file, "%s\t%2.2f\t%s\t%2.2f\t%s\t%2.2f\t%s" %(line1.strip(),fp,fp_p,pp_l,pp_l_p,pp_r,pp_r_p) 
        #print >>out_file, "%s\t%d\t%2.2f\t%d\t%2.2f\t%d\t%2.2f" %(line1.strip(),fp,float(fp_p)/abs(end1-start1),pp_l,float(pp_l_p)/abs(end1-start1),pp_r,float(pp_r_p)/abs(end1-start1)) 
    """
    fo=open("pfct","w")
    print >>fo, g1
    print >>fo, g2
    try:
        for line in mycoverage([g1,g2]):
            if type( line ) is GenomicInterval:
                print >> out_file, "\t".join( line.fields )
            else:
                print >> out_file, line
                
    except ParseError, exc:
        print >> sys.stderr, "Invalid file format: ", str( exc )

    if g1.skipped > 0:
        print skipped( g1, filedesc=" of 1st dataset" )

    if g2.skipped > 0:
        print skipped( g2, filedesc=" of 2nd dataset" )

        """
if __name__ == "__main__":
    main()
