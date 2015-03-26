#!/usr/bin/env python
"""
Creates a config file and then run the Bic-Seq tool.
usage: Bic-Seq.py [options]
   --NBam: Normal BAM file
   --TBam: Tumor BAM file
   --NTemp: Normal Tempfile from Samtools
   --TTemp: Tumor Tempfile from Samtools
   --config_file: Config file created for temp files
   --png_file: PNG Result file
   --bicseg_file: BICSEG Result file
   --wig_file: WIG Result file
"""

import optparse, os, sys, subprocess, tempfile, shutil

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '', '--NBam', dest='NBam', help='The normal input BAM file' )
    parser.add_option( '', '--TBam', dest='TBam', help='The tumor input BAM file' )
    parser.add_option( '', '--NTemp', dest='NTemp', help='The normal temp file' )
    parser.add_option( '', '--TTemp', dest='TTemp', help='The tumor temp file' )
    parser.add_option( '', '--config_file', dest='config_file', help='Config File created for temp files' )
    parser.add_option( '', '--png_file', dest='png_file', help='PNG Result file' )
    parser.add_option( '', '--bicseg_file', dest='bicseg_file', help='BICSEG Result file' )
    parser.add_option( '', '--wig_file', dest='wig_file', help='WIG Result file' )
    ( options, args ) = parser.parse_args()
 
    # STEP1: Call the makebicseqconfig.pl script to create a config file
    tmp_dir = tempfile.mkdtemp( dir='.' )
    try:
        #Need to move this script to /opt/installed
        configfile_script = "/opt/installed/galaxy-dist/tools/Suzi_pipeline/makebicseqconfig.pl"
	command = '%s %s %s %s %s ' % ( configfile_script, options.TBam, options.NBam, options.TTemp, options.NTemp )
	tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
	tmp_stderr = open( tmp, 'wb' )
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
	# get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp, 'rb' )
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
        if returncode != 0:
            raise Exception, stderr
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )
        stop_err( 'Error creating config file for (%s) and (%s), %s' % ( options.NBam, options.TBam, str( e ) ) )

    # Move to our output dataset location
    output_file = '%s/tumor_sorted.bam_vs_normal_sorted.bam_config.txt' % os.path.abspath(tmp_dir)
    shutil.move( output_file, options.config_file )
    #clean up temp files
    if os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )
    # check that there are results in the output file
    if os.path.getsize( options.config_file ) > 0:
        sys.stdout.write( 'Config File created.' )
    else:
        stop_err( 'Error creating config file' )
    

    # STEP2: Call the BIC-seq.pl script to run the BIC-Seq tool and produce results
    try:
	#bicseqout temp directory
        tmp_dir_bicseqout = tempfile.mkdtemp(dir='.')
        #results tag name
        tmp_results_file = tempfile.NamedTemporaryFile( dir=tmp_dir_bicseqout )
        tmp_results_file_name = tmp_results_file.name
        result_name = os.path.basename(tmp_results_file_name)
        tmp_results_file.close()
	#Need to move this tool to /opt/installed
        BIC_seq_script = "/mnt/lustre1/users/feis/BICseq/PERLpipeline/BICseq_1.1.2/BIC-seq/BIC-seq.pl"
        command = '%s --lambda=15 --bin_size=100 --paired %s %s %s ' % ( BIC_seq_script, options.config_file, tmp_dir_bicseqout, result_name)
        tmp = tempfile.NamedTemporaryFile( dir=tmp_dir_bicseqout ).name
        tmp_stderr = open( tmp, 'wb' )
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir_bicseqout, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
        # get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp, 'rb' )
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
        if returncode != 0:
            raise Exception, stderr
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir_bicseqout ):
            shutil.rmtree( tmp_dir_bicseqout )
        stop_err( 'Error running BIC-Seq tool. %s' % str( e ) )
    
    # Move to our output dataset location
    png_file = '%s/%s/%s.png' % (tmp_dir_bicseqout, tmp_dir_bicseqout, result_name) 
    shutil.move( png_file, options.png_file )
    bicseg_file = '%s/%s/%s.bicseg' % (tmp_dir_bicseqout, tmp_dir_bicseqout, result_name) 
    shutil.move( bicseg_file, options.bicseg_file )
    wig_file = '%s/%s/%s.wig' % (tmp_dir_bicseqout, tmp_dir_bicseqout, result_name) 
    shutil.move( wig_file, options.wig_file )
    #clean up temp files
    if os.path.exists( tmp_dir_bicseqout ):
        shutil.rmtree( tmp_dir_bicseqout )
    # check that there are results in the output file
    if os.path.getsize( options.png_file and options.bicseg_file and options.wig_file ) > 0:
        sys.stdout.write( 'BIC-Seq results created.' )
    else:
        stop_err( 'Error creating BIC-Seq results file' )
    
if __name__=="__main__": __main__()
