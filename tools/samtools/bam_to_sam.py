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
    parser.add_option( '', '--header', dest='header', action='store_true', default=False, help='Write SAM Header' )
    ( options, args ) = parser.parse_args()

    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='samtools 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( 'Samtools %s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine Samtools version\n' )

    tmp_dir = tempfile.mkdtemp( dir='.' )

    try:
        # exit if input file empty
        if os.path.getsize( options.input1 ) == 0:
            raise Exception, 'Initial BAM file empty'
        # Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created. This command
        # may also create temporary files <out.prefix>.%d.bam when the whole alignment cannot be fitted
        # into memory ( controlled by option -m ).
        tmp_sorted_aligns_file = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmp_sorted_aligns_file_base = tmp_sorted_aligns_file.name
        tmp_sorted_aligns_file_name = '%s.bam' % tmp_sorted_aligns_file.name
        tmp_sorted_aligns_file.close()
        command = 'samtools sort %s %s' % ( options.input1, tmp_sorted_aligns_file_base )
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
        # exit if sorted BAM file empty
        if os.path.getsize( tmp_sorted_aligns_file_name) == 0:
            raise Exception, 'Intermediate sorted BAM file empty'
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )
        stop_err( 'Error sorting alignments from (%s), %s' % ( options.input1, str( e ) ) )


    try:
        # Extract all alignments from the input BAM file to SAM format ( since no region is specified, all the alignments will be extracted ).
        if options.header:
            view_options = "-h"
        else:
            view_options = ""
        command = 'samtools view %s -o %s %s' % ( view_options, options.output1, tmp_sorted_aligns_file_name )
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
