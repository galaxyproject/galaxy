#! /usr/bin/python

"""
Creates a pileup file from a bam file and a reference.

usage: %prog [options]
   -p, --input1=p: bam file
   -o, --output1=o: Output pileup
   -R, --ref=R: Reference file type
   -n, --ownFile=n: User-supplied fasta reference file
   -d, --dbkey=d: dbkey of user-supplied file
   -x, --indexDir=x: Index directory
   -b, --bamIndex=b: BAM index file
   -s, --lastCol=s: Print the mapping quality as the last column
   -i, --indels=i: Only output lines containing indels
   -M, --mapCap=M: Cap mapping quality
   -c, --consensus=c: Call the consensus sequence using MAQ consensu model
   -T, --theta=T: Theta paramter (error dependency coefficient)
   -N, --hapNum=N: Number of haplotypes in sample
   -r, --fraction=r: Expected fraction of differences between a pair of haplotypes
   -I, --phredProb=I: Phred probability of an indel in sequencing/prep

"""

import os, sys, tempfile
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( msg )
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
    seq_path = check_seq_file( options.dbkey, options.indexDir )
    tmp_dir = tempfile.gettempdir()
    os.chdir(tmp_dir)
    tmpf0 = tempfile.NamedTemporaryFile(dir=tmp_dir)
    tmpf0bam = '%s.bam' % tmpf0.name
    tmpf0bambai = '%s.bam.bai' % tmpf0.name
    tmpf1 = tempfile.NamedTemporaryFile(dir=tmp_dir)
    tmpf1fai = '%s.fai' % tmpf1.name
    opts = '%s %s -M %s' % (('','-s')[options.lastCol=='yes'], ('','-i')[options.indels=='yes'], options.mapCap)
    if options.consensus == 'yes':
        opts += ' -c -T %s -N %s -r %s -I %s' % (options.theta, options.hapNum, options.fraction, options.phredProb)
    cmd1 = None
    cmd2 = 'cp %s %s; cp %s %s' % (options.input1, tmpf0bam, options.bamIndex, tmpf0bambai)
    cmd3 = 'samtools pileup %s -f %s %s > %s 2> /dev/null'
    if options.ref =='indexed':
        full_path = "%s.fai" % seq_path 
        if not os.path.exists( full_path ):
            stop_err( "No sequences are available for '%s', request them by reporting this error." % options.dbkey )
        cmd3 = cmd3 % (opts, seq_path, tmpf0bam, options.output1)
    elif options.ref == 'history':
        cmd1 = 'cp %s %s; cp %s.fai %s' % (options.ownFile, tmpf1.name, options.ownFile, tmpf1fai)
        cmd3 = cmd3 % (opts, tmpf1.name, tmpf0bam, options.output1)
    # index reference if necessary
    if cmd1:
        try:
            os.system(cmd1)
        except Exception, eq:
            stop_err('Error moving reference sequence\n' + str(eq))
    # copy bam index to working directory
    try:
        os.system(cmd2)
    except Exception, eq:
        stop_err('Error moving files to temp directory\n' + str(eq))
    # perform pileup command
    try:
        os.system(cmd3)
    except Exception, eq:
        stop_err('Error running SAMtools merge tool\n' + str(eq))
    # clean up temp files
    tmpf1.close()
    tmpf0.close()
    if os.path.exists(tmpf0bam):
        os.remove(tmpf0bam)
    if os.path.exists(tmpf0bambai):
        os.remove(tmpf0bambai)
    if os.path.exists(tmpf1fai):
        os.remove(tmpf0bambai)
            
if __name__ == "__main__" : __main__()
