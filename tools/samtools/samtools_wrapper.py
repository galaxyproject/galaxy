#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for running SAMTools commands.
"""

import sys, optparse, os, tempfile, subprocess, shutil
from string import Template

GALAXY_EXT_TO_SAMTOOLS_EXT = { 'bam_index':'bam.bai', } #items not listed here will use the galaxy extension as-is
GALAXY_EXT_TO_SAMTOOLS_FILE_TYPE = GALAXY_EXT_TO_SAMTOOLS_EXT #for now, these are the same, but could be different if needed
DEFAULT_SAMTOOLS_PREFIX = "SAMTools_file"
CHUNK_SIZE = 2**20 #1mb


def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

def SAMTOOLS_filename_from_galaxy( galaxy_filename, galaxy_ext, target_dir = None, prefix = None ):
    suffix = GALAXY_EXT_TO_SAMTOOLS_EXT.get( galaxy_ext, galaxy_ext )
    if prefix is None:
        prefix = DEFAULT_SAMTOOLS_PREFIX
    if target_dir is None:
        target_dir = os.getcwd()
    SAMTools_filename = os.path.join( target_dir, "%s.%s" % ( prefix, suffix ) )
    os.symlink( galaxy_filename, SAMTools_filename )
    return SAMTools_filename

def SAMTOOLS_filetype_argument_substitution( argument, galaxy_ext ):
    return argument % dict( file_type = GALAXY_EXT_TO_SAMTOOLS_FILE_TYPE.get( galaxy_ext, galaxy_ext ) )

def open_file_from_option( filename, mode = 'rb' ):
    if filename:
        return open( filename, mode = mode )
    return None

def html_report_from_directory( html_out, dir ):
    html_out.write( '<html>\n<head>\n<title>Galaxy - SAMTOOLS Output</title>\n</head>\n<body>\n<p/>\n<ul>\n' )
    for fname in sorted( os.listdir( dir ) ):
        html_out.write(  '<li><a href="%s">%s</a></li>\n' % ( fname, fname ) )
    html_out.write( '</ul>\n</body>\n</html>\n' )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--pass_through', dest='pass_through_options', action='append', type="string", help='These options are passed through directly to SAMTOOLS, without any modification.' )
    parser.add_option( '-d', '--dataset', dest='datasets', action='append', type="string", nargs=4, help='"-argument" "original_filename" "galaxy_filetype" "name_prefix"' )
    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )
    parser.add_option( '', '--html_report_from_directory', dest='html_report_from_directory', action='append', type="string", nargs=2, help='"Target HTML File" "Directory"')
    (options, args) = parser.parse_args()
    
    tmp_dir = tempfile.mkdtemp( prefix='tmp-SAMTOOLS-' )
    
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( prefix="SAMTOOLS-stderr-", dir=tmp_dir )
    
    if options.pass_through_options:
        cmd = ' '.join( options.pass_through_options )
    else:
        cmd = ''
    return_code = None
    if options.datasets:
        for ( dataset_arg, filename, galaxy_ext, prefix ) in options.datasets:
            SAMTools_filename = SAMTOOLS_filename_from_galaxy( filename, galaxy_ext, target_dir = tmp_dir, prefix = prefix )
            if dataset_arg:
                if '>' in cmd:
                    cmd = cmd.replace( '>', '  %s "%s" >' % ( SAMTOOLS_filetype_argument_substitution( dataset_arg, galaxy_ext ), SAMTools_filename ), 1 )
                else:
                    cmd = '%s %s "%s"' % ( cmd, SAMTOOLS_filetype_argument_substitution( dataset_arg, galaxy_ext ), SAMTools_filename )
            #auto index fasta files:
            if galaxy_ext == 'fa':
                index_cmd = 'samtools faidx %s' % ( SAMTools_filename )
                proc = subprocess.Popen( args=index_cmd, stdout=stdout, stderr=stderr, shell=True, cwd=tmp_dir )
                return_code = proc.wait()
                if return_code:
                    break
    if return_code is None or not return_code:
        proc = subprocess.Popen( args=cmd, stdout=stdout, stderr=stderr, shell=True, cwd=tmp_dir )
        return_code = proc.wait()
    if return_code:
        stderr_target = sys.stderr
    else:
        if stdout:
            stderr_target = stdout
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
    #generate html reports
    if options.html_report_from_directory:
        for ( html_filename, html_dir ) in options.html_report_from_directory:
            html_report_from_directory( open( html_filename, 'wb' ), html_dir )
    
    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
