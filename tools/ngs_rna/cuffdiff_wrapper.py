#!/usr/bin/env python

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    
    # Cuffdiff options.
    parser.add_option( '-s', '--inner-dist-std-dev', dest='inner_dist_std_dev', help='The standard deviation for the distribution on inner distances between mate pairs. The default is 20bp.' )
    parser.add_option( '-p', '--num-threads', dest='num_threads', help='Use this many threads to align reads. The default is 1.' )
    parser.add_option( '-m', '--inner-mean-dist', dest='inner_mean_dist', help='This is the expected (mean) inner distance between mate pairs. \
                                                                                For, example, for paired end runs with fragments selected at 300bp, \
                                                                                where each end is 50bp, you should set -r to be 200. The default is 45bp.')
    parser.add_option( '-Q', '--min-mapqual', dest='min_mapqual', help='Instructs Cufflinks to ignore alignments with a SAM mapping quality lower than this number. The default is 0.' )
    parser.add_option( '-c', '--min-alignment-count', dest='min_alignment_count', help='The minimum number of alignments in a locus for needed to conduct significance testing on changes in that locus observed between samples. If no testing is performed, changes in the locus are deemed not signficant, and the locus\' observed changes don\'t contribute to correction for multiple testing. The default is 1,000 fragment alignments (up to 2,000 paired reads).' )
    parser.add_option( '--FDR', dest='FDR', help='The allowed false discovery rate. The default is 0.05.' )

    # Advanced Options:	
    parser.add_option( '--num-importance-samples', dest='num_importance_samples', help='Sets the number of importance samples generated for each locus during abundance estimation. Default: 1000' )
    parser.add_option( '--max-mle-iterations', dest='max_mle_iterations', help='Sets the number of iterations allowed during maximum likelihood estimation of abundances. Default: 5000' )
    
    # Wrapper / Galaxy options.
    parser.add_option( '-A', '--inputA', dest='inputA', help='A transcript GTF file produced by cufflinks, cuffcompare, or other source.')
    parser.add_option( '-1', '--input1', dest='input1', help='File of RNA-Seq read alignments in the SAM format. SAM is a standard short read alignment, that allows aligners to attach custom tags to individual alignments, and Cufflinks requires that the alignments you supply have some of these tags. Please see Input formats for more details.' )
    parser.add_option( '-2', '--input2', dest='input2', help='File of RNA-Seq read alignments in the SAM format. SAM is a standard short read alignment, that allows aligners to attach custom tags to individual alignments, and Cufflinks requires that the alignments you supply have some of these tags. Please see Input formats for more details.' )

    parser.add_option( "--isoforms_fpkm_tracking_output", dest="isoforms_fpkm_tracking_output" )
    parser.add_option( "--genes_fpkm_tracking_output", dest="genes_fpkm_tracking_output" )
    parser.add_option( "--cds_fpkm_tracking_output", dest="cds_fpkm_tracking_output" )
    parser.add_option( "--tss_groups_fpkm_tracking_output", dest="tss_groups_fpkm_tracking_output" )
    parser.add_option( "--isoforms_exp_output", dest="isoforms_exp_output" )
    parser.add_option( "--genes_exp_output", dest="genes_exp_output" )
    parser.add_option( "--tss_groups_exp_output", dest="tss_groups_exp_output" )
    parser.add_option( "--cds_exp_fpkm_tracking_output", dest="cds_exp_fpkm_tracking_output" )
    parser.add_option( "--splicing_diff_output", dest="splicing_diff_output" )
    parser.add_option( "--cds_diff_output", dest="cds_diff_output" )
    parser.add_option( "--promoters_diff_output", dest="promoters_diff_output" )
    
    (options, args) = parser.parse_args()
    
    # Make temp directory for output.
    tmp_output_dir = tempfile.mkdtemp()
    
    # Build command.
    
    # Base.
    cmd = "cuffdiff"
    
    # Add options.
    if options.inner_dist_std_dev:
        cmd += ( " -s %i" % int ( options.inner_dist_std_dev ) )
    if options.num_threads:
        cmd += ( " -p %i" % int ( options.num_threads ) )
    if options.inner_mean_dist:
        cmd += ( " -m %i" % int ( options.inner_mean_dist ) )
    if options.min_mapqual:
        cmd += ( " -Q %i" % int ( options.min_mapqual ) )
    if options.min_alignment_count:
        cmd += ( " -c %i" % int ( options.min_alignment_count ) )
    if options.FDR:
        cmd += ( " --FDR %f" % float( options.FDR ) )
    if options.num_importance_samples:
        cmd += ( " --num-importance-samples %i" % int ( options.num_importance_samples ) )
    if options.max_mle_iterations:
        cmd += ( " --max-mle-iterations %i" % int ( options.max_mle_iterations ) )
            
    # Add inputs.
    cmd += " " + options.inputA + " " + options.input1 + " " + options.input2

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
        if len( open( tmp_output_dir + "/isoforms.fpkm_tracking", 'rb' ).read().strip() ) == 0:
            raise Exception, 'The main output file is empty, there may be an error with your input file or settings.'
    except Exception, e:
        stop_err( 'Error running cuffdiff. ' + str( e ) )

        
    # Copy output files from tmp directory to specified files.
    try:
        try:
            shutil.copyfile( tmp_output_dir + "/isoforms.fpkm_tracking", options.isoforms_fpkm_tracking_output )
            shutil.copyfile( tmp_output_dir + "/genes.fpkm_tracking", options.genes_fpkm_tracking_output )
            shutil.copyfile( tmp_output_dir + "/cds.fpkm_tracking", options.cds_fpkm_tracking_output )
            shutil.copyfile( tmp_output_dir + "/tss_groups.fpkm_tracking", options.tss_groups_fpkm_tracking_output )
            shutil.copyfile( tmp_output_dir + "/0_1_isoform_exp.diff", options.isoforms_exp_output )
            shutil.copyfile( tmp_output_dir + "/0_1_gene_exp.diff", options.genes_exp_output )
            shutil.copyfile( tmp_output_dir + "/0_1_tss_group_exp.diff", options.tss_groups_exp_output )
            shutil.copyfile( tmp_output_dir + "/0_1_splicing.diff", options.splicing_diff_output )
            shutil.copyfile( tmp_output_dir + "/0_1_cds.diff", options.cds_diff_output )
            shutil.copyfile( tmp_output_dir + "/0_1_cds_exp.diff", options.cds_diff_output )
            shutil.copyfile( tmp_output_dir + "/0_1_promoters.diff", options.promoters_diff_output )    
        except Exception, e:
            stop_err( 'Error in cuffdiff:\n' + str( e ) ) 
    finally:
        # Clean up temp dirs
        if os.path.exists( tmp_output_dir ):
            shutil.rmtree( tmp_output_dir )

if __name__=="__main__": __main__()