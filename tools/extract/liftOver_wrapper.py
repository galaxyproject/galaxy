#!/usr/bin/env python
#Guruprasad Ananda
"""
Converts coordinates from one build/assembly to another using liftOver binary and mapping files downloaded from UCSC.
"""

import os, string, subprocess, sys
import tempfile
import re

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def safe_bed_file(infile):
    """Make a BED file with track and browser lines ready for liftOver.

    liftOver will fail with track or browser lines. We can make it happy
    by converting these to comments. See:

    https://lists.soe.ucsc.edu/pipermail/genome/2007-May/013561.html
    """
    fix_pat = re.compile("^(track|browser)")
    (fd, fname) = tempfile.mkstemp()
    in_handle = open(infile)
    out_handle = open(fname, "w")
    for line in in_handle:
        if fix_pat.match(line):
            line = "#" + line
        out_handle.write(line)
    in_handle.close()
    out_handle.close()
    return fname
    
if len( sys.argv ) < 9:
    stop_err( "USAGE: prog input out_file1 out_file2 input_dbkey output_dbkey infile_type minMatch multiple <minChainT> <minChainQ> <minSizeQ>" )

infile = sys.argv[1]
outfile1 = sys.argv[2]
outfile2 = sys.argv[3]
in_dbkey = sys.argv[4]
mapfilepath = sys.argv[5]
infile_type = sys.argv[6]
gff_option = ""
if infile_type == "gff":
    gff_option = "-gff "
minMatch = sys.argv[7]
multiple = int(sys.argv[8])
multiple_option = ""
if multiple:
    minChainT = sys.argv[9]
    minChainQ = sys.argv[10]
    minSizeQ = sys.argv[11]
    multiple_option = " -multiple -minChainT=%s -minChainQ=%s -minSizeQ=%s " %(minChainT,minChainQ,minSizeQ)

try:
    assert float(minMatch)
except:
    minMatch = 0.1
#ensure dbkey is set
if in_dbkey == "?": 
    stop_err( "Input dataset genome build unspecified, click the pencil icon in the history item to specify it." )

if not os.path.isfile( mapfilepath ):
    stop_err( "%s mapping is not currently available."  % ( mapfilepath.split('/')[-1].split('.')[0] ) )

safe_infile = safe_bed_file(infile)
cmd_line = "liftOver " + gff_option + "-minMatch=" + str(minMatch) + multiple_option + " "  + safe_infile + " " + mapfilepath + " " + outfile1 + " " + outfile2 + "  > /dev/null"

try:
    # have to nest try-except in try-finally to handle 2.4
    try:
        proc = subprocess.Popen( args=cmd_line, shell=True, stderr=subprocess.PIPE )
        returncode = proc.wait()
        stderr = proc.stderr.read()
        if returncode != 0:
            raise Exception, stderr
    except Exception, e:
        raise Exception, 'Exception caught attempting conversion: ' + str( e )
finally:
    os.remove(safe_infile)
