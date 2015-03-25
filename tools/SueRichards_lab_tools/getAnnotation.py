#!/usr/bin/env python
#Adapted from Dan Blankenberg

"""
A wrapper script for running the SeattleSeq getAnnotation jarfile
"""

import sys, optparse, os, tempfile, subprocess, shutil

CHUNK_SIZE = 2**20 #1mb

def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

def open_file_from_option( filename, mode = 'rb' ):
    if filename:
        return open( filename, mode = mode )
    return None

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--pass_through', dest='pass_through_options', action='store', type="string", help='These options are passed through directly to the getAnnotation jarfile, without any modification.' )
    parser.add_option( '-i', '--input', dest='input_file', action='store', type="string", default=None, help='Input vcf file')
    parser.add_option( '-o', '--output', dest='output_file', action='store', type="string", default=None, help='Output txt file')
    parser.add_option( '-d', '--database_info', dest='input_database_info', action='store', type="string", default=None, help='Login information for annotationCache database')

    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )

    (options, args) = parser.parse_args()
   
    #   Do not believe we need to use a temporary directory for this tool; could likely be commented out
    tmp_dir = tempfile.mkdtemp( prefix='tmp-GATK-' )
    if options.pass_through_options:
        cmd = ' '.join( options.pass_through_options )
    else:
        cmd = ''
    
    assert None not in [ options.input_file, options.output_file, options.input_database_info ], 'You must specify both input and output files, plus database login info'
    print "Pass-through options:"
    print options.pass_through_options
    print "Input file:"
    print options.input_file
    print "Output file:"
    print options.output_file
    print "Database login file:"
    print options.input_database_info

    cmd = '%s -i %s -o %s -d %s' % ( options.pass_through_options, options.input_file, options.output_file, options.input_database_info )
    print "Command:"
    print cmd
    
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    if stdout is None:
        stdout = sys.stdout
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( prefix="GATK-stderr-", dir=tmp_dir )

    #   Execute command and check for errors
    proc = subprocess.Popen( args=cmd, stdout=stdout, stderr=stderr, shell=True, cwd=tmp_dir )
    return_code = proc.wait()
    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    stderr.flush()
    stderr.seek(0)
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()

    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()



