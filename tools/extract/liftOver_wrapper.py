#!/usr/bin/env python2.4
#Guru
"""
Converts coordinates from one build/assembly to another using liftOver binary and mapping files downloaded from UCSC.
"""

import sys, os, string

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
if len(sys.argv) != 6:
    stop_error("USAGE: prog input out_file1 out_file2 input_dbkey output_dbkey")

infile = sys.argv[1]
outfile1 = sys.argv[2]
outfile2 = sys.argv[3]
in_dbkey = sys.argv[4]
out_dbkey = sys.argv[5]

#ensure dbkeys are set
if in_dbkey == "?": 
    stop_err("You must specify a build to the input dataset in order to covert genome coordinates.")
if out_dbkey == "?": 
    stop_err("Please specify a build for the output dataset using the 'To' dropdown menu.")

#Check if the apping file exists    
#example file path: hg18ToHg17.over.chain
mapfilename = in_dbkey + "To" + out_dbkey[0].capitalize() + out_dbkey[1:] + ".over.chain"
mapfilepath = "/depot/data2/galaxy/" + in_dbkey + "/liftOver/" + mapfilename
try:
    open(mapfilepath, 'r')
except Exception, ex:
    stop_err("Mapping information from %s to %s is unavailable." %(in_dbkey, out_dbkey))
    
print "Mapping from %s to %s" %(in_dbkey,out_dbkey)
try:
    cmd_line = "liftOver " + infile + " " + mapfilepath + " " + outfile1 + " " + outfile2 + "  > /dev/null 2>&1"
    os.system(cmd_line)
except Exception, exc:
    print >>sys.stderr, exc
  
    
