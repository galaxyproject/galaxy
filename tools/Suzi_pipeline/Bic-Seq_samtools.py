#!/usr/bin/env python
"""
Uses a custom samtools to create a temp file for the provided BAM file.
usage: Bic-Seq_samtools.py [options]
   --input: input bam file 
   --output: temp file
"""

import optparse, os, sys, subprocess, tempfile, shutil

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '', '--input1', dest='input1', help='The input BAM file' )
    parser.add_option( '', '--threads', dest='threads', help='Number of threads' )
    parser.add_option( '', '--output1', dest='output1', help='The output BAM dataset' )
    ( options, args ) = parser.parse_args()
 
    # Need to move this to /opt/installed
    samtools_path = "/mnt/lustre1/users/feis/BICseq/PERLpipeline/BICseq_1.1.2/SAMgetUnique/samtools-0.1.7a_getUnique-0.1.1/samtools"

    # output version # of tool
    try:
        command = '%s 2 >&1' % samtools_path
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args=command, shell=True, stdout=tmp_stdout ) 
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( '%s %s\n' % (samtools_path, stdout) )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine %s version\n' % samtools_path )

    
    #STEP1: Run samtools for the input BAM file and create a temp file
    tmp_dir = tempfile.mkdtemp( dir='.' )
    try:
        tmp_file = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmp_file_name = tmp_file.name
        tmp_file.close()
        command = '%s view -U Bowtie,%s,N,N %s ' % ( samtools_path, tmp_file_name, options.input1 ) #use options.threads for threading
	tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
        tmp_stderr = open( tmp, 'wb' )
        print command
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )
        stop_err( 'Error creating temp file for (%s), %s' % ( options.input1, str( e ) ) )

    # Move to our output dataset location
    ## Currently only one file. Need to work on the logic for all chromosomes.
    output_file = '%schr22.seq' % tmp_file_name
    shutil.move( output_file, options.output1 )
    #clean up temp files
    if os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )
    # check that there are results in the output file
    if os.path.getsize( options.output1 ) > 0:
        sys.stdout.write( 'Temp File created.' )
    else:
        stop_err( 'Error copying temp file for BAM file.' )

if __name__=="__main__": __main__()
