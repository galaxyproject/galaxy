#! /usr/bin/python

import optparse, os, shutil, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-1', '--input1', dest='input1', help='The (forward or single-end) reads file in Sanger FASTQ format' )
    parser.add_option( '-2', '--input2', dest='input2', help='The reverse reads file in Sanger FASTQ format' )
    parser.add_option( '-a', '--min-anchor-length', dest='min_anchor_length', 
                        help='The "anchor length". TopHat will report junctions spanned by reads with at least this many bases on each side of the junction.' )
    parser.add_option( '-i', '--min-intron-length', dest='min_intron_length', 
                        help='The minimum intron length. TopHat will ignore donor/acceptor pairs closer than this many bases apart.' )
    parser.add_option( '-I', '--max-intron-length', dest='max_intron_length', 
                        help='The maximum intron length. When searching for junctions ab initio, TopHat will ignore donor/acceptor pairs farther than this many bases apart, except when such a pair is supported by a split segment alignment of a long read.' )
    parser.add_option( '-s', '--solexa-quals', dest='solexa_quals', help='Use the Solexa scale for quality values in FASTQ files.' )
    parser.add_option( '-S', '--solexa.3-quals', dest='solexa_quals', 
                        help='As of the Illumina GA pipeline version 1.3, quality scores are encoded in Phred-scaled base-64. Use this option for FASTQ files from pipeline 1.3 or later.' )
    parser.add_option( '-p', '--num-threads', dest='num_threads', help='Use this many threads to align reads. The default is 1.' )
    parser.add_option( '-C', '--coverage-output', dest='coverage_output_file', help='Coverage output file; formate is WIG.' )
    parser.add_option( '-J', '--junctions-output', dest='junctions_output_file', help='Junctions output file; formate is BED.' )
    parser.add_option( '-H', '--hits-output', dest='accepted_hits_output_file', help='Accepted hits output file; formate is SAM.' )
    parser.add_option( '-D', '--indexes-dir', dest='indexes_directory', help='Indexes directory; location of .ebwt and .fa files.' )
    parser.add_option( '-r', '--mate-inner-dist', dest='mate_inner_dist', help='This is the expected (mean) inner distance between mate pairs. \
                                                                                For, example, for paired end runs with fragments selected at 300bp, \
                                                                                where each end is 50bp, you should set -r to be 200. There is no default, \
                                                                                and this parameter is required for paired end runs.')
    (options, args) = parser.parse_args()
    
    # Make temp directory for output.
    tmp_output_dir = tempfile.mkdtemp()
    
    # Build command.
    
    # Base.
    cmd = "tophat -o %s " % ( tmp_output_dir )
    
    # Add options.
    if options.mate_inner_dist:
        cmd += ( " -r %i" % int ( options.mate_inner_dist ) )
        
    # Add index prefix.
    cmd += " " + options.indexes_directory
        
    # Add input files.
    cmd += " " + options.input1
    if options.mate_inner_dist:
        # Using paired-end reads.
        cmd += " " + options.input2
        
    # Route program output to file.
    cmd += " > %s" % tmp_output_dir + "/std_out.txt"
    # Route program error output to file.
    cmd += " 2> %s" % tmp_output_dir + "/std_err.txt"

    # Run.
    try:
        os.system( cmd )
    except Exception, e:
        stop_err( 'Error in tophat:\n' + str( e ) )
        
    # TODO: look for errors in program output.
        
    # Copy output files from tmp directory to specified files.
    try:
        shutil.copyfile( tmp_output_dir + "/coverage.wig", options.coverage_output_file )
        shutil.copyfile( tmp_output_dir + "/junctions.bed", options.junctions_output_file )
        shutil.copyfile( tmp_output_dir + "/accepted_hits.sam", options.accepted_hits_output_file )
    except Exception, e:
        stop_err( 'Error in tophat:\n' + str( e ) ) 

    # Clean up temp dirs
    if os.path.exists( tmp_output_dir ):
        shutil.rmtree( tmp_output_dir )

if __name__=="__main__": __main__()
