#!/usr/bin/env python

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-r', dest='ref_annotation', help='An optional "reference" annotation GTF. Each sample is matched against this file, and sample isoforms are tagged as overlapping, matching, or novel where appropriate. See the refmap and tmap output file descriptions below.' )
    parser.add_option( '-R', action="store_true", dest='ignore_nonoverlap', help='If -r was specified, this option causes cuffcompare to ignore reference transcripts that are not overlapped by any transcript in one of cuff1.gtf,...,cuffN.gtf. Useful for ignoring annotated transcripts that are not present in your RNA-Seq samples and thus adjusting the "sensitivity" calculation in the accuracy report written in the transcripts accuracy file' )
    
    # Wrapper / Galaxy options.
    parser.add_option( '-1', dest='input1')
    parser.add_option( '-2', dest='input2')
    parser.add_option( '-A', '--transcripts-accuracy-output', dest='transcripts_accuracy_output_file', help='' )
    parser.add_option( '-B', '--transcripts-combined-output', dest='transcripts_combined_output_file', help='' )
    parser.add_option( '-C', '--transcripts-tracking-output', dest='transcripts_tracking_output_file', help='' )
    parser.add_option( '', '--input1-tmap-output', dest='input1_tmap_output_file', help='' )
    parser.add_option( '', '--input1-refmap-output', dest='input1_refmap_output_file', help='' )
    parser.add_option( '', '--input2-tmap-output', dest='input2_tmap_output_file', help='' )
    parser.add_option( '', '--input2-refmap-output', dest='input2_refmap_output_file', help='' )
    
    
    (options, args) = parser.parse_args()
    
    # Make temp directory for output.
    tmp_output_dir = tempfile.mkdtemp()
    
    # Build command.
    
    # Base.
    cmd = "cuffcompare -o cc_output"
    
    # Add options.
    if options.ref_annotation:
        cmd += " -r %s" % options.ref_annotation
    if options.ignore_nonoverlap:
        cmd += " -R "
        
    # Add input files.
        
    # Need to symlink inputs so that output files are written to temp directory.
    input1_file_name = tmp_output_dir + "/input1"
    os.symlink( options.input1,  input1_file_name )
    cmd += " %s" % input1_file_name
    two_inputs = ( options.input2 != None)
    if two_inputs:
        input2_file_name = tmp_output_dir + "/input2"
        os.symlink( options.input2, input2_file_name )
        cmd += " %s" % input2_file_name
    
    # Run command.
    try:        
        tmp_name = tempfile.NamedTemporaryFile( dir=tmp_output_dir ).name
        tmp_stderr = open( tmp_name, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, cwd=tmp_output_dir, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
        
        # Get stderr, allowing for case where it's very large.
        tmp_stderr = open( tmp_name, 'rb' )
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += tmp_stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        tmp_stderr.close()
        
        # Error checking.
        if returncode != 0:
            raise Exception, stderr
            
        # check that there are results in the output file
        if len( open( tmp_output_dir + "/cc_output", 'rb' ).read().strip() ) == 0:
            raise Exception, 'The main output file is empty, there may be an error with your input file or settings.'
    except Exception, e:
        stop_err( 'Error running cuffcompare. ' + str( e ) )
        
    # Copy output files from tmp directory to specified files.
    try:
        try:
            shutil.copyfile( tmp_output_dir + "/cc_output", options.transcripts_accuracy_output_file )
            shutil.copyfile( tmp_output_dir + "/input1.tmap", options.input1_tmap_output_file )
            shutil.copyfile( tmp_output_dir + "/input1.refmap", options.input1_refmap_output_file )
            if two_inputs:
                shutil.copyfile( tmp_output_dir + "/cc_output.combined.gtf", options.transcripts_combined_output_file )
                shutil.copyfile( tmp_output_dir + "/cc_output.tracking", options.transcripts_tracking_output_file )
                shutil.copyfile( tmp_output_dir + "/input2.tmap", options.input2_tmap_output_file )
                shutil.copyfile( tmp_output_dir + "/input2.refmap", options.input2_refmap_output_file )
        except Exception, e:
            stop_err( 'Error in cuffcompare:\n' + str( e ) ) 
    finally:
        # Clean up temp dirs
        if not os.path.exists( tmp_output_dir ):
            shutil.rmtree( tmp_output_dir )

if __name__=="__main__": __main__()