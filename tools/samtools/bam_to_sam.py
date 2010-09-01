#!/usr/bin/env python
"""
Converts BAM data to sorted SAM data.
usage: bam_to_sam.py [options]
   --input1: SAM file to be converted
   --output1: output dataset in bam format
"""

import optparse, os, sys, subprocess, tempfile, shutil
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
#from galaxy import util

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '', '--input1', dest='input1', help='The input SAM dataset' )
    parser.add_option( '', '--output1', dest='output1', help='The output BAM dataset' )
    ( options, args ) = parser.parse_args()

    tmp_dir = tempfile.mkdtemp()
    try:
        # exit if input file empty
        if os.path.getsize( options.input1 ) == 0:
            raise Exception, 'Initial BAM file empty'
        # Extract all alignments from the input BAM file to SAM format ( since no region is specified, all the alignments will be extracted ).
        command = 'samtools view -o %s %s' % ( options.output1, options.input1 )
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
        stop_err( 'Error extracting alignments from (%s), %s' % ( options.input1, str( e ) ) )
    #clean up temp files
    if os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )
    # check that there are results in the output file
    if os.path.getsize( options.output1 ) > 0:
        sys.stdout.write( 'BAM file converted to SAM' )
    else:
        stop_err( 'The output file is empty, there may be an error with your input file.' )

if __name__=="__main__": __main__()
