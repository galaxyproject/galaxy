#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for running the MINE.jar commands.
"""

import sys, optparse, os, tempfile, subprocess, shutil

CHUNK_SIZE = 2**20 #1mb

BASE_NAME = "galaxy_mime_file.txt"
JOB_ID = "galaxy_mine"

def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        print os.listdir( tmp_dir )
        shutil.rmtree( tmp_dir )

def open_file_from_option( filename, mode = 'rb' ):
    if filename:
        return open( filename, mode = mode )
    return None


def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-j', '--jar', dest='jar', action='store', type="string", help='Location of JAR file' )
    parser.add_option( '-i', '--infile', dest='infile', action='store', type="string", help='infile' )
    parser.add_option( '-m', '--master_variable', dest='master_variable', action='store', type="string", help='master_variable' )
    parser.add_option( '-v', '--cv', dest='cv', action='store', type="string", help='cv' )
    parser.add_option( '-e', '--exp', dest='exp', action='store', type="string", help='exp' )
    parser.add_option( '-c', '--c', dest='c', action='store', type="string", help='c' )
    parser.add_option( '-p', '--permute', dest='permute', action='store_true', default=False, help='permute' )
    parser.add_option( '-o', '--output_results', dest='output_results', action='store', type="string", help='output_results' )
    parser.add_option( '-l', '--output_log', dest='output_log', action='store', type="string", help='output_log' )
    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )
    (options, args) = parser.parse_args()
    
    tmp_dir = tempfile.mkdtemp( prefix='tmp-MINE-' )
    tmp_input_name = os.path.join( tmp_dir, BASE_NAME )
    if options.permute:
        permute = "-permute"
    else:
        permute = ""
    
    os.symlink( options.infile, tmp_input_name )
    
    cmd = 'java -jar "%s" "%s" %s -cv%s -exp%s -c%s %s "%s"' % ( options.jar, tmp_input_name, options.master_variable, options.cv, options.exp, options.c, permute, JOB_ID )
    print cmd
    
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( prefix="MINE-stderr-", dir=tmp_dir )
    
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
    
    print os.listdir( tmp_dir )
    
    shutil.move( '%s,%s,Results.csv' % ( tmp_input_name, JOB_ID ), options.output_results )
    shutil.move( '%s,%s,Status.csv' % ( tmp_input_name, JOB_ID ), options.output_log )
    
    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
