#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for slicing a BAM file by provided BED file using SAMTools.
%prog input_filename.sam output_filename.bam
"""
#TODO: Confirm that the sort is necessary e.g. if input regions are out of order


import sys, optparse, os, tempfile, subprocess, shutil

CHUNK_SIZE = 2**20 #1mb

def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    
    assert len( args ) == 4, "Invalid command line: samtools_slice_bam.py input.bam input.bam.bai input.interval output.bam"
    input_bam_filename, input_index_filename, input_interval_filename, output_bam_filename = args
    
    tmp_dir = tempfile.mkdtemp( prefix='tmp-samtools_slice_bam-' )
    
    tmp_input_bam_filename = os.path.join( tmp_dir, 'input_bam.bam' )
    os.symlink( input_bam_filename, tmp_input_bam_filename )
    os.symlink( input_index_filename, "%s.bai" % tmp_input_bam_filename )
    
    #Slice BAM
    unsorted_bam_filename = os.path.join( tmp_dir, 'unsorted.bam' )
    unsorted_stderr_filename = os.path.join( tmp_dir, 'unsorted.stderr' )
    cmd = 'samtools view -b -L "%s" "%s" > "%s"' % ( input_interval_filename, tmp_input_bam_filename, unsorted_bam_filename )
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
    #TODO: confirm if sorting is necessary (is original BAM order maintained, or does the output follow the order of input intervals?)
    sorted_stderr_filename = os.path.join( tmp_dir, 'sorted.stderr' )
    sorting_prefix = os.path.join( tmp_dir, 'sorted_bam' )
    cmd = 'samtools sort -o "%s" "%s" > "%s"' % ( unsorted_bam_filename, sorting_prefix, output_bam_filename )
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
