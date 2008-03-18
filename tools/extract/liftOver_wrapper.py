#!/usr/bin/env python2.4
#Guruprasad Ananda
"""
Converts coordinates from one build/assembly to another using liftOver binary and mapping files downloaded from UCSC.
"""

import sys, os, string

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
if len( sys.argv ) != 6:
    stop_err( "USAGE: prog input out_file1 out_file2 input_dbkey output_dbkey" )

infile = sys.argv[1]
outfile1 = sys.argv[2]
outfile2 = sys.argv[3]
in_dbkey = sys.argv[4]
out_dbkey = sys.argv[5]

#ensure dbkeys are set
if in_dbkey == "?": 
    stop_err( "Input dataset genome build unspecified, click the pencil icon in hte history item to specify it." )
if out_dbkey == "?": 
    stop_err( "No build selected for conversion." )

#Check if the Mapping file exists    
#example file path: hg18ToHg17.over.chain
mapfilename = in_dbkey + "To" + out_dbkey.capitalize()  + ".over.chain"
# TODO: Ticket # 167 - These hard-coded paths need to be removed
mapfilepath = "/depot/data2/galaxy/" + in_dbkey + "/liftOver/" + mapfilename
cmd_line = "liftOver " + infile + " " + mapfilepath + " " + outfile1 + " " + outfile2 + "  > /dev/null 2>&1"

if not os.path.isfile( mapfilepath ):
    stop_err( "Mapping information from %s to %s is not currently available."  % ( in_dbkey, out_dbkey ) )
try:
    os.system( cmd_line )
except Exception, exc:
    stop_err( "Exception caught attempting conversion: %s"  % str( exc ) )

print "%s converted to %s" % ( in_dbkey, out_dbkey )
  
    
