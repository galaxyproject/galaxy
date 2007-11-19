#!/usr/bin/env python

"""
Adapted from bx/scripts/qv_to_bqv.py

Convert a qual (qv) file to several BinnedArray files for fast seek.
This script takes approximately 4 seconds per 1 million base pairs.

The input format is fasta style quality -- fasta headers followed by 
whitespace separated integers.

usage: %prog qual_file output_file
"""

import pkg_resources 
pkg_resources.require( "bx-python" )
pkg_resources.require( "numpy" )
import string
import psyco_full
import sys, re, os, tempfile
from bx.binned_array import BinnedArrayWriter
from bx.cookbook import *
import fileinput

def load_scores_ba_dir( dir ):
    """
    Return a dict-like object (keyed by chromosome) that returns 
    FileBinnedArray objects created from "key.ba" files in `dir`
    """
    return FileBinnedArrayDir( dir )

def main():
    args = sys.argv[1:]
    try:
        qual_file_dir = args[0]
        #mydir="/home/gua110/Desktop/chimp_quality_scores/chr22.qa"
        mydir="/home/gua110/Desktop/rhesus_quality_scores/rheMac2.qual.qv"
        qual_file_dir = mydir.replace(mydir.split("/")[-1], "")
        output_file = args[ 1 ]
        fo = open(output_file,"w")
    except:
        print "usage: qual_file output_file"
        sys.exit()
    
    tmpfile = tempfile.NamedTemporaryFile()
    cmdline = "ls " + qual_file_dir + "*.qa | cat >> " + tmpfile.name
    os.system (cmdline)
    for qual_file in tmpfile.readlines():
        qual = fileinput.FileInput( qual_file.strip() )
        outfile = None
        outbin = None
        base_count = 0
        mega_count = 0
    
        for line in qual:
            line = line.rstrip("\r\n")
            if line.startswith(">"):
                # close old
                if outbin and outfile:
                    print "\nFinished region " + region + " at " + str(base_count) + " base pairs."
                    outbin.finish()
                    outfile.close()
                # start new file
                region = line.lstrip(">")
                #outfname = output_file + "." + region + ".bqv" #CHANGED
                outfname = qual_file.strip() + ".bqv"
                print >>fo, "Writing region " + region + " to file " + outfname
                outfile = open( outfname , "wb")
                outbin = BinnedArrayWriter(outfile, typecode='b', default=0)
                base_count = 0
                mega_count = 0
            else:
                if outfile and outbin:
                    nums = line.split()
                    for val in nums:
                        outval = int(val)
                        assert outval <= 255 and outval >= 0
                        outbin.write(outval)
                        base_count += 1
                    if (mega_count * 1000000) <= base_count:
                        sys.stdout.write(str(mega_count)+" ")
                        sys.stdout.flush()
                        mega_count = base_count // 1000000 + 1
        if outbin and outfile:
            print "\nFinished region " + region + " at " + str(base_count) + " base pairs."
            outbin.finish()
            outfile.close()

if __name__ == "__main__":
    main()
