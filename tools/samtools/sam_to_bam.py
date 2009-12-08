#! /usr/bin/python
"""
Converts SAM data to sorted BAM data.
usage: sam_to_bam.py [options]
   --input1: SAM file to be converted
   --dbkey: dbkey value
   --ref_file: Reference file if choosing from history
   --output1: output dataset in bam format
   --index_dir: GALAXY_DATA_INDEX_DIR
"""

import optparse, os, sys, subprocess, tempfile, shutil, gzip
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
from galaxy import util

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def check_seq_file( dbkey, cached_seqs_pointer_file ):
    seq_path = ''
    for line in open( cached_seqs_pointer_file ):
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
    parser = optparse.OptionParser()
    parser.add_option( '', '--input1', dest='input1', help='The input SAM dataset' )
    parser.add_option( '', '--dbkey', dest='dbkey', help='The build of the reference dataset' )
    parser.add_option( '', '--ref_file', dest='ref_file', help='The reference dataset from the history' )
    parser.add_option( '', '--output1', dest='output1', help='The output BAM dataset' )
    parser.add_option( '', '--index_dir', dest='index_dir', help='GALAXY_DATA_INDEX_DIR' )
    ( options, args ) = parser.parse_args()

    cached_seqs_pointer_file = "%s/sam_fa_indices.loc" % options.index_dir
    if not os.path.exists( cached_seqs_pointer_file ):
        stop_err( "The required file (%s) does not exist." % cached_seqs_pointer_file )
    # If found for the dbkey, seq_path will look something like /depot/data2/galaxy/equCab2/sam_index/equCab2.fa,
    # and the equCab2.fa file will contain fasta sequences.
    seq_path = check_seq_file( options.dbkey, cached_seqs_pointer_file )
    tmp_dir = tempfile.gettempdir()
    if options.ref_file == "None":
        # We're using locally cached reference sequences( e.g., /depot/data2/galaxy/equCab2/sam_index/equCab2.fa ).
        # The indexes for /depot/data2/galaxy/equCab2/sam_index/equCab2.fa will be contained in
        # a file named /depot/data2/galaxy/equCab2/sam_index/equCab2.fa.fai
        fai_index_file_path = "%s.fai" % seq_path 
        if not os.path.exists( fai_index_file_path ):
            stop_err( "No sequences are available for build (%s), request them by reporting this error." % options.dbkey )
    else:
        try:
            # Create indexes for history reference ( e.g., ~/database/files/000/dataset_1.dat ) using samtools faidx, which will:
            # - index reference sequence in the FASTA format or extract subsequence from indexed reference sequence
            # - if no region is specified, faidx will index the file and create <ref.fasta>.fai on the disk
            # - if regions are specified, the subsequences will be retrieved and printed to stdout in the FASTA format
            # - the input file can be compressed in the RAZF format.
            # IMPORTANT NOTE: a real weakness here is that we are creating indexes for the history dataset
            # every time we run this tool.  It would be nice if we could somehow keep track of user's specific
            # index files so they could be re-used.
            fai_index_file_path = os.path.join( tmp_dir, os.path.basename( options.ref_file ) )
            # At this point, fai_index_file_path will look something like /tmp/dataset_13.dat
            os.symlink( options.ref_file, fai_index_file_path )
            command = "samtools faidx %s 2>/dev/null" % fai_index_file_path
            proc = subprocess.Popen( args=command, shell=True )
            proc.wait()
        except Exception, e:
            stop_err( 'Error creating indexes from reference (%s), %s' % ( options.ref_file, str( e ) ) )
    try:
        # Extract all alignments from the input SAM file to BAM format ( since no region is specified, all the alignments will be extracted ).
        tmp_aligns_file = tempfile.NamedTemporaryFile()
        tmp_aligns_file_name = tmp_aligns_file.name
        tmp_aligns_file.close()
        # IMPORTANT NOTE: for some reason the samtools view command gzips the resulting bam file without warning,
        # and the docs do not currently state that this occurs ( very bad ).
        command = "samtools view -bt %s -o %s %s 2>/dev/null" % ( fai_index_file_path, tmp_aligns_file_name, options.input1 ) 
        proc = subprocess.Popen( args=command, shell=True )
        proc.wait()
    except Exception, e:
        stop_err( 'Error extracting alignments from (%s), %s' % ( options.input1, str( e ) ) )
    try:
        # Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created. This command
        # may also create temporary files <out.prefix>.%d.bam when the whole alignment cannot be fitted
        # into memory ( controlled by option -m ).
        tmp_sorted_aligns_file = tempfile.NamedTemporaryFile()
        tmp_sorted_aligns_file_name = tmp_sorted_aligns_file.name
        tmp_sorted_aligns_file.close()
        command = "samtools sort %s %s 2>/dev/null" % ( tmp_aligns_file_name, tmp_sorted_aligns_file_name )
        proc = subprocess.Popen( args=command, shell=True )
        proc.wait()
    except Exception, e:
        stop_err( 'Error sorting alignments from (%s), %s' % ( tmp_aligns_file_name, str( e ) ) )
    # Move tmp_aligns_file_name to our output dataset location
    sorted_bam_file = '%s.bam' % tmp_sorted_aligns_file_name
    shutil.move( sorted_bam_file, options.output1 )
    if options.ref_file != "None":
        # Remove the symlink from /tmp/dataset_13.dat to ~/database/files/000/dataset_13.dat
        os.unlink( fai_index_file_path )
        # Remove the index file
        index_file_name = '%s.fai' % fai_index_file_path
        os.unlink( index_file_name )
    # Remove the tmp_aligns_file_name
    os.unlink( tmp_aligns_file_name )

if __name__=="__main__": __main__()
