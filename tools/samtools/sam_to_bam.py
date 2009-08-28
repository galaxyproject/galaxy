#! /usr/bin/python

"""
Converts SAM data to BAM format.

usage: %prog [options]
   -i, --input1=i: SAM file to be converted
   -d, --dbkey=d: dbkey value
   -r, --ref_file=r: Reference file if choosing from history
   -o, --output1=o: BAM output
   -x, --index_dir=x: Index directory

usage: %prog input_file dbkey ref_list output_file
"""

import os, sys, tempfile
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def check_seq_file( dbkey, GALAXY_DATA_INDEX_DIR ):
    seq_file = "%s/sam_fa_indices.loc" % GALAXY_DATA_INDEX_DIR
    seq_path = ''
    for line in open( seq_file ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ) and line.startswith( 'index' ):
            fields = line.split( '\t' )
            if len( fields ) < 3:
                continue
            if fields[1] == dbkey:
                seq_path = fields[2].strip()
                break
    return seq_path
 
def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    seq_path = check_seq_file( options.dbkey, options.index_dir )
    tmp_dir = tempfile.gettempdir()
    os.chdir(tmp_dir)
    tmpf1 = tempfile.NamedTemporaryFile(dir=tmp_dir)
    tmpf1fai = '%s.fai' % tmpf1.name
    tmpf2 = tempfile.NamedTemporaryFile(dir=tmp_dir)
    tmpf3 = tempfile.NamedTemporaryFile(dir=tmp_dir)
    tmpf3bam = '%s.bam' % tmpf3.name
    if options.ref_file == "None":
        full_path = "%s.fai" % seq_path 
        if not os.path.exists( full_path ):
            stop_err( "No sequences are available for '%s', request them by reporting this error." % options.dbkey )
        cmd1 = "cp %s %s; cp %s %s" % (seq_path, tmpf1.name, full_path, tmpf1fai)
    else:
        cmd1 = "cp %s %s; samtools faidx %s 2>/dev/null" % (options.ref_file, tmpf1.name, tmpf1.name) 
    cmd2 = "samtools view -bt %s -o %s %s 2>/dev/null" % (tmpf1fai, tmpf2.name, options.input1)   
    cmd3 = "samtools sort %s %s 2>/dev/null" % (tmpf2.name, tmpf3.name)
    cmd4 = "cp %s %s" % (tmpf3bam, options.output1)
    # either create index based on fa file or copy provided index to temp directory 
    try:
        os.system(cmd1)
    except Exception, eq:
        stop_err("Error creating the reference list index.\n" + str(eq))
    # create original bam file
    try:
        os.system(cmd2)
    except Exception, eq:
        stop_err("Error running view command.\n" + str(eq))
    # sort original bam file to produce sorted output bam file
    try:
        os.system(cmd3)
        os.system(cmd4)
    except Exception, eq:
        stop_err("Error sorting data and creating output file.\n" + str(eq))
    # cleanup temp files
    tmpf1.close()
    tmpf2.close()
    tmpf3.close()
    if os.path.exists(tmpf1fai):
        os.remove(tmpf1fai)
    if os.path.exists(tmpf3bam):
        os.remove(tmpf3bam)

if __name__=="__main__": __main__()
