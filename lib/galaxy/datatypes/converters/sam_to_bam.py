#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for converting SAM to BAM, with sorting.
%prog input_filename.sam output_filename.bam
"""

import sys, optparse, os, tempfile, subprocess, shutil

CHUNK_SIZE = 2**20 #1mb


def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()

    assert len( args ) == 2, 'You must specify the input and output filenames'
    input_filename, output_filename = args

    tmp_dir = tempfile.mkdtemp( prefix='tmp-sam_to_bam_converter-' )

    #convert to SAM
    unsorted_bam_filename = os.path.join( tmp_dir, 'unsorted.bam' )
    unsorted_stderr_filename = os.path.join( tmp_dir, 'unsorted.stderr' )
    cmd = 'samtools view -bS "%s" > "%s"' % ( input_filename, unsorted_bam_filename )
    proc = subprocess.Popen( args=cmd, stderr=open( unsorted_stderr_filename, 'wb' ), shell=True, cwd=tmp_dir )
    return_code = proc.wait()
    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    stderr = open( unsorted_stderr_filename )
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()

    #sort sam, so indexing will not fail
    sorted_stderr_filename = os.path.join( tmp_dir, 'sorted.stderr' )
    sorting_prefix = os.path.join( tmp_dir, 'sorted_bam' )
    cmd = 'samtools sort -o "%s" "%s" > "%s"' % ( unsorted_bam_filename, sorting_prefix, output_filename )
    proc = subprocess.Popen( args=cmd, stderr=open( sorted_stderr_filename, 'wb' ), shell=True, cwd=tmp_dir )
    return_code = proc.wait()

    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    stderr = open( sorted_stderr_filename )
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()

    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
