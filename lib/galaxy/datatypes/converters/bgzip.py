#!/usr/bin/env python

"""
Uses pysam to bgzip a file

usage: %prog in_file out_file
"""

from galaxy import eggs
import pkg_resources; pkg_resources.require( "pysam" )
import ctabix, subprocess, tempfile, sys

def main():
    filetype, input_fname, out_fname = sys.argv[1:]
    
    tmpfile = tempfile.NamedTemporaryFile()
    sort_params = None
    
    if filetype == "bed":
        sort_params = ["sort", "-k1,1", "-k2,2n", "-k3,3n"]
    elif filetype == "vcf":
        sort_params = ["sort", "-k1,1", "-k2,2n"]
    elif filetype == "gff":
        sort_params = ["sort", "-s", "-k1,1", "-k4,4n"] # stable sort on start column
    # Skip any lines starting with "#" and "track"
    grepped = subprocess.Popen(["grep", "-e", "^\"#\"", "-e", "^track", "-v", input_fname], stderr=subprocess.PIPE, stdout=subprocess.PIPE )
    after_sort = subprocess.Popen(sort_params, stdin=grepped.stdout, stderr=subprocess.PIPE, stdout=tmpfile )
    grepped.stdout.close()
    output, err = after_sort.communicate()
    
    ctabix.tabix_compress(tmpfile.name, out_fname, force=True)
    
if __name__ == "__main__": 
    main()
    