#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for running SICER (spatial clustering approach for the identification of ChIP-enriched regions) region caller.
"""

import sys, optparse, os, tempfile, subprocess, shutil

CHUNK_SIZE = 2**20 #1mb

VALID_BUILDS = [ 'mm8', 'mm9', 'hg18', 'hg19', 'dm2', 'dm3', 'sacCer1', 'pombe', 'rn4', 'tair8' ] #HACK! FIXME: allow using all specified builds, would currently require hacking SICER's "GenomeData.py" on the fly.

def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )


def open_file_from_option( filename, mode = 'rb' ):
    if filename:
        return open( filename, mode = mode )
    return None

def add_one_to_file_column( filename, column, split_char = "\t", startswith_skip = None ):
    tmp_out = tempfile.TemporaryFile( mode='w+b' )
    tmp_in = open( filename )
    for line in tmp_in:
        if startswith_skip and line.startswith( startswith_skip ):
            tmp_out.write( line )
        else:
            fields = line.rstrip( '\n\r' ).split( split_char )
            if len( fields ) <= column:
                tmp_out.write( line )
            else:
                fields[ column ] = str( int( fields[ column ] ) + 1 )
                tmp_out.write( "%s\n" % ( split_char.join( fields )  ) )
    tmp_in.close()
    tmp_out.seek( 0 )
    tmp_in = open( filename, 'wb' )
    while True:
        chunk = tmp_out.read( CHUNK_SIZE )
        if chunk:
            tmp_in.write( chunk )
        else:
            break
    tmp_in.close()
    tmp_out.close()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    #stdout/err
    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )
    parser.add_option( '', '--fix_off_by_one_errors', dest='fix_off_by_one_errors', action='store_true', default=False, help='If specified, fix off-by-one errors in output files' )
    #inputs
    parser.add_option( '-b', '--bed_file', dest='bed_file', action='store', type="string", default=None, help='Input ChIP BED file.' )
    parser.add_option( '-c', '--control_file', dest='control_file', action='store', type="string", default=None, help='Input control BED file.' )
    parser.add_option( '-d', '--dbkey', dest='dbkey', action='store', type="string", default=None, help='Input dbkey.' )
    parser.add_option( '-r', '--redundancy_threshold', dest='redundancy_threshold', action='store', type="int", default=1, help='Redundancy Threshold: The number of copies of identical reads allowed in a library.' )
    parser.add_option( '-w', '--window_size', dest='window_size', action='store', type="int", default=200, help='Window size: resolution of SICER algorithm. For histone modifications, one can use 200 bp' )
    parser.add_option( '-f', '--fragment_size', dest='fragment_size', action='store', type="int", default=150, help='Fragment size: is for determination of the amount of shift from the beginning of a read to the center of the DNA fragment represented by the read. FRAGMENT_SIZE=150 means the shift is 75.' )
    parser.add_option( '-e', '--effective_genome_fraction', dest='effective_genome_fraction', action='store', type="float", default=0.74, help='Effective genome fraction: Effective Genome as fraction of the genome size. It depends on read length.' )
    parser.add_option( '-g', '--gap_size', dest='gap_size', action='store', type="int", default=600, help='Gap size: needs to be multiples of window size. Namely if the window size is 200, the gap size should be 0, 200, 400, 600, ... .' )
    parser.add_option( '-o', '--error_cut_off', dest='error_cut_off', action='store', type="string", default="0.1", help='Error Cut off: FDR or E-value' ) #read as string to construct names properly
    #outputs
    parser.add_option( '', '--redundancy_removed_test_bed_output_file', dest='redundancy_removed_test_bed_output_file', action='store', type="string", default=None, help='test-1-removed.bed: redundancy_removed test bed file' )
    parser.add_option( '', '--redundancy_removed_control_bed_output_file', dest='redundancy_removed_control_bed_output_file', action='store', type="string", default=None, help='control-1-removed.bed: redundancy_removed control bed file' )
    parser.add_option( '', '--summary_graph_output_file', dest='summary_graph_output_file', action='store', type="string", default=None, help='test-W200.graph: summary graph file for test-1-removed.bed with window size 200, in bedGraph format.' )
    parser.add_option( '', '--test_normalized_wig_output_file', dest='test_normalized_wig_output_file', action='store', type="string", default=None, help='test-W200-normalized.wig: the above file normalized by library size per million and converted into wig format. This file can be uploaded to the UCSC genome browser' )
    parser.add_option( '', '--score_island_output_file', dest='score_island_output_file', action='store', type="string", default=None, help='test-W200-G600.scoreisland: an intermediate file for debugging usage.' )
    parser.add_option( '', '--islands_summary_output_file', dest='islands_summary_output_file', action='store', type="string", default=None, help='test-W200-G600-islands-summary: summary of all candidate islands with their statistical significance.' )
    parser.add_option( '', '--significant_islands_summary_output_file', dest='significant_islands_summary_output_file', action='store', type="string", default=None, help='test-W200-G600-islands-summary-FDR.01: summary file of significant islands with requirement of FDR=0.01.' )
    parser.add_option( '', '--significant_islands_output_file', dest='significant_islands_output_file', action='store', type="string", default=None, help='test-W200-G600-FDR.01-island.bed: delineation of significant islands in "chrom start end read-count-from-redundancy_removed-test.bed" format' )
    parser.add_option( '', '--island_filtered_output_file', dest='island_filtered_output_file', action='store', type="string", default=None, help='test-W200-G600-FDR.01-islandfiltered.bed: library of raw redundancy_removed reads on significant islands.' )
    parser.add_option( '', '--island_filtered_normalized_wig_output_file', dest='island_filtered_normalized_wig_output_file', action='store', type="string", default=None, help='test-W200-G600-FDR.01-islandfiltered-normalized.wig: wig file for the island-filtered redundancy_removed reads.' )
    (options, args) = parser.parse_args()
    
    #check if valid build
    assert options.dbkey in VALID_BUILDS, ValueError( "The specified build ('%s') is not available for this tool." % options.dbkey )
    
    #everything will occur in this temp directory
    tmp_dir = tempfile.mkdtemp()
    
    #link input files into tmp_dir and build command line
    bed_base_filename = 'input_bed_file'
    bed_filename = '%s.bed' % bed_base_filename
    os.symlink( options.bed_file, os.path.join( tmp_dir, bed_filename ) )
    if options.control_file is not None:
        cmd = "SICER.sh"
    else:
        cmd = "SICER-rb.sh"
    cmd = '%s "%s" "%s"' % ( cmd, tmp_dir, bed_filename )
    if options.control_file is not None:
        control_base_filename = 'input_control_file'
        control_filename = '%s.bed' % control_base_filename
        os.symlink( options.control_file, os.path.join( tmp_dir, control_filename ) )
        cmd = '%s "%s"' % ( cmd, control_filename )
    cmd = '%s "%s" "%s" "%i" "%i" "%i" "%f" "%i" "%s"' % ( cmd, tmp_dir, options.dbkey, options.redundancy_threshold, options.window_size, options.fragment_size, options.effective_genome_fraction, options.gap_size, options.error_cut_off )
    
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( dir=tmp_dir )
        stderr.close()
        stderr = open( stderr.name, 'w+b' )
    
    proc = subprocess.Popen( args=cmd, stdout=stdout, stderr=stderr, shell=True, cwd=tmp_dir )
    return_code = proc.wait()
    
    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = stdout #sys.stdout
        stderr_target.write( "\nAdditionally, these warnings were reported:\n" )
    stderr.flush()
    stderr.seek(0)
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()
    
    try:
        #move files to where they belong
        shutil.move(  os.path.join( tmp_dir,'%s-%i-removed.bed' % ( bed_base_filename, options.redundancy_threshold ) ), options.redundancy_removed_test_bed_output_file )
        shutil.move(  os.path.join( tmp_dir,'%s-W%i.graph' % ( bed_base_filename, options.window_size ) ), options.summary_graph_output_file )
        if options.fix_off_by_one_errors: add_one_to_file_column( options.summary_graph_output_file, 2 )
        shutil.move(  os.path.join( tmp_dir,'%s-W%i-normalized.wig' % ( bed_base_filename, options.window_size ) ), options.test_normalized_wig_output_file )
        if options.control_file is not None:
            shutil.move(  os.path.join( tmp_dir,'%s-%i-removed.bed' % ( control_base_filename, options.redundancy_threshold ) ), options.redundancy_removed_control_bed_output_file )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i.scoreisland' % ( bed_base_filename, options.window_size, options.gap_size ) ), options.score_island_output_file )
            if options.fix_off_by_one_errors: add_one_to_file_column( options.score_island_output_file, 2 )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-islands-summary' % ( bed_base_filename, options.window_size, options.gap_size ) ), options.islands_summary_output_file )
            if options.fix_off_by_one_errors: add_one_to_file_column( options.islands_summary_output_file, 2 )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-islands-summary-FDR%s' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.significant_islands_summary_output_file )
            if options.fix_off_by_one_errors: add_one_to_file_column( options.significant_islands_summary_output_file, 2 )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-FDR%s-island.bed' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.significant_islands_output_file )
            if options.fix_off_by_one_errors: add_one_to_file_column( options.significant_islands_output_file, 2 )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-FDR%s-islandfiltered.bed' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.island_filtered_output_file )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-FDR%s-islandfiltered-normalized.wig' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.island_filtered_normalized_wig_output_file )
        else:
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-E%s.scoreisland' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.score_island_output_file )
            if options.fix_off_by_one_errors: add_one_to_file_column( options.score_island_output_file, 2 )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-E%s-islandfiltered.bed' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.island_filtered_output_file )
            shutil.move(  os.path.join( tmp_dir,'%s-W%i-G%i-E%s-islandfiltered-normalized.wig' % ( bed_base_filename, options.window_size, options.gap_size, options.error_cut_off ) ), options.island_filtered_normalized_wig_output_file )
    except Exception, e:
        raise e
    finally:
        cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
