#!/usr/bin/env python

import sys, argparse, os, subprocess, shutil

def __main__():

    #Parse Command Line
    parser = argparse.ArgumentParser()

    parser.add_argument( 'outfile', action='store', type=str, help='Output file name for concatenated files' )
    parser.add_argument( 'infiles', action='store', type=str, nargs='+', help='Input file names to concatenate separated by spaces' )

 
    options = parser.parse_args()
    outfile = options.outfile
    print outfile 
    infiles = options.infiles
    print infiles
    
    # if there is more than 1 input file
    # concatenate the files to produce one result file
    # if there are multiple gzipped input files this will result
    # in one gzipped file 
    if len(infiles) > 1:
#      cmdline = "zcat "
       cmdline = "cat "
       for inp in infiles:
          cmdline = cmdline + inp + " "
#         cmdline = cmdline + "| gzip >" + outfile
       cmdline = cmdline + " >" + outfile
       print cmdline
       try:
          subprocess.check_output(args=cmdline, stderr=subprocess.STDOUT, shell=True)
       except subprocess.CalledProcessError, e:
          print "!!!!!!!!!!!!concatenate ERROR: stdout output:\n", e.output

if __name__=="__main__": __main__()

