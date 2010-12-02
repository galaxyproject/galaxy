#!/usr/bin/env python

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-1', '--input', dest='input', help=' file of RNA-Seq read alignments in the SAM format. SAM is a standard short read alignment, that allows aligners to attach custom tags to individual alignments, and Cufflinks requires that the alignments you supply have some of these tags. Please see Input formats for more details.' )
    parser.add_option( '-s', '--inner-dist-std-dev', dest='inner_dist_std_dev', help='The standard deviation for the distribution on inner distances between mate pairs. The default is 20bp.' )
    parser.add_option( '-I', '--max-intron-length', dest='max_intron_len', help='The minimum intron length. Cufflinks will not report transcripts with introns longer than this, and will ignore SAM alignments with REF_SKIP CIGAR operations longer than this. The default is 300,000.' )
    parser.add_option( '-F', '--min-isoform-fraction', dest='min_isoform_fraction', help='After calculating isoform abundance for a gene, Cufflinks filters out transcripts that it believes are very low abundance, because isoforms expressed at extremely low levels often cannot reliably be assembled, and may even be artifacts of incompletely spliced precursors of processed transcripts. This parameter is also used to filter out introns that have far fewer spliced alignments supporting them. The default is 0.05, or 5% of the most abundant isoform (the major isoform) of the gene.' )
    parser.add_option( '-j', '--pre-mrna-fraction', dest='pre_mrna_fraction', help='Some RNA-Seq protocols produce a significant amount of reads that originate from incompletely spliced transcripts, and these reads can confound the assembly of fully spliced mRNAs. Cufflinks uses this parameter to filter out alignments that lie within the intronic intervals implied by the spliced alignments. The minimum depth of coverage in the intronic region covered by the alignment is divided by the number of spliced reads, and if the result is lower than this parameter value, the intronic alignments are ignored. The default is 5%.' )
    parser.add_option( '-p', '--num-threads', dest='num_threads', help='Use this many threads to align reads. The default is 1.' )
    parser.add_option( '-m', '--inner-mean-dist', dest='inner_mean_dist', help='This is the expected (mean) inner distance between mate pairs. \
                                                                                For, example, for paired end runs with fragments selected at 300bp, \
                                                                                where each end is 50bp, you should set -r to be 200. The default is 45bp.')
    parser.add_option( '-Q', '--min-mapqual', dest='min_mapqual', help='Instructs Cufflinks to ignore alignments with a SAM mapping quality lower than this number. The default is 0.' )
    parser.add_option( '-G', '--GTF', dest='GTF', help='Tells Cufflinks to use the supplied reference annotation to estimate isoform expression. It will not assemble novel transcripts, and the program will ignore alignments not structurally compatible with any reference transcript.' )

    # Advanced Options:	
    parser.add_option( '--num-importance-samples', dest='num_importance_samples', help='Sets the number of importance samples generated for each locus during abundance estimation. Default: 1000' )
    parser.add_option( '--max-mle-iterations', dest='max_mle_iterations', help='Sets the number of iterations allowed during maximum likelihood estimation of abundances. Default: 5000' )
    
    # Wrapper / Galaxy options.
    parser.add_option( '-A', '--assembled-isoforms-output', dest='assembled_isoforms_output_file', help='Assembled isoforms output file; formate is GTF.' )
    parser.add_option( '-T', '--transcripts-expression-output', dest='transcripts_expression_output_file', help='TODO' )
    parser.add_option( '-Z', '--genes-expression-output', dest='genes_expression_output_file', help='TODO' )
    
    (options, args) = parser.parse_args()
    
    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='cufflinks 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'cufflinks v' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( '%s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine Cufflinks version\n' )

    # Make temp directory for output.
    tmp_output_dir = tempfile.mkdtemp()
    
    # Build command.
    
    # Base.
    cmd = "cufflinks"
    
    # Add options.
    if options.inner_dist_std_dev:
        cmd += ( " -s %i" % int ( options.inner_dist_std_dev ) )
    if options.max_intron_len:
        cmd += ( " -I %i" % int ( options.max_intron_len ) )
    if options.min_isoform_fraction:
        cmd += ( " -F %f" % float ( options.min_isoform_fraction ) )
    if options.pre_mrna_fraction:
        cmd += ( " -j %f" % float ( options.pre_mrna_fraction ) )    
    if options.num_threads:
        cmd += ( " -p %i" % int ( options.num_threads ) )
    if options.inner_mean_dist:
        cmd += ( " -m %i" % int ( options.inner_mean_dist ) )
    if options.min_mapqual:
        cmd += ( " -Q %i" % int ( options.min_mapqual ) )
    if options.GTF:
        cmd += ( " -G %s" % options.GTF )
    if options.num_importance_samples:
        cmd += ( " --num-importance-samples %i" % int ( options.num_importance_samples ) )
    if options.max_mle_iterations:
        cmd += ( " --max-mle-iterations %i" % int ( options.max_mle_iterations ) )
        
    # Add input files.
    cmd += " " + options.input
    
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
    except Exception, e:
        stop_err( 'Error running cufflinks. ' + str( e ) )
        
    # Copy output files from tmp directory to specified files.
    try:
        try:
            shutil.copyfile( os.path.join( tmp_output_dir, "transcripts.gtf" ), options.assembled_isoforms_output_file )
            shutil.copyfile( os.path.join( tmp_output_dir, "transcripts.expr" ), options.transcripts_expression_output_file )
            shutil.copyfile( os.path.join( tmp_output_dir, "genes.expr" ), options.genes_expression_output_file )
        except Exception, e:
            stop_err( 'Error in tophat:\n' + str( e ) ) 
    finally:
        # Clean up temp dirs
        if os.path.exists( tmp_output_dir ):
            shutil.rmtree( tmp_output_dir )

if __name__=="__main__": __main__()
