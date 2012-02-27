#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for running the GenomeAnalysisTK.jar commands.
"""

import sys, optparse, os, tempfile, subprocess, shutil
from binascii import unhexlify
from string import Template

GALAXY_EXT_TO_GATK_EXT = { 'gatk_interval':'intervals', 'bam_index':'bam.bai', 'gatk_dbsnp':'dbSNP', 'picard_interval_list':'interval_list' } #items not listed here will use the galaxy extension as-is
GALAXY_EXT_TO_GATK_FILE_TYPE = GALAXY_EXT_TO_GATK_EXT #for now, these are the same, but could be different if needed
DEFAULT_GATK_PREFIX = "gatk_file"
CHUNK_SIZE = 2**20 #1mb


def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

def gatk_filename_from_galaxy( galaxy_filename, galaxy_ext, target_dir = None, prefix = None ):
    suffix = GALAXY_EXT_TO_GATK_EXT.get( galaxy_ext, galaxy_ext )
    if prefix is None:
        prefix = DEFAULT_GATK_PREFIX
    if target_dir is None:
        target_dir = os.getcwd()
    gatk_filename = os.path.join( target_dir, "%s.%s" % ( prefix, suffix ) )
    os.symlink( galaxy_filename, gatk_filename )
    return gatk_filename

def gatk_filetype_argument_substitution( argument, galaxy_ext ):
    return argument % dict( file_type = GALAXY_EXT_TO_GATK_FILE_TYPE.get( galaxy_ext, galaxy_ext ) )

def open_file_from_option( filename, mode = 'rb' ):
    if filename:
        return open( filename, mode = mode )
    return None

def html_report_from_directory( html_out, dir ):
    html_out.write( '<html>\n<head>\n<title>Galaxy - GATK Output</title>\n</head>\n<body>\n<p/>\n<ul>\n' )
    for fname in sorted( os.listdir( dir ) ):
        html_out.write(  '<li><a href="%s">%s</a></li>\n' % ( fname, fname ) )
    html_out.write( '</ul>\n</body>\n</html>\n' )

def index_bam_files( bam_filenames, tmp_dir ):
    for bam_filename in bam_filenames:
        bam_index_filename = "%s.bai" % bam_filename
        if not os.path.exists( bam_index_filename ):
            #need to index this bam file
            stderr_name = tempfile.NamedTemporaryFile( prefix = "bam_index_stderr" ).name
            command = 'samtools index %s %s' % ( bam_filename, bam_index_filename )
            proc = subprocess.Popen( args=command, shell=True, stderr=open( stderr_name, 'wb' ) )
            return_code = proc.wait()
            if return_code:
                for line in open( stderr_name ):
                    print >> sys.stderr, line
                os.unlink( stderr_name ) #clean up
                cleanup_before_exit( tmp_dir )
                raise Exception( "Error indexing BAM file" )
            os.unlink( stderr_name ) #clean up

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--pass_through', dest='pass_through_options', action='append', type="string", help='These options are passed through directly to GATK, without any modification.' )
    parser.add_option( '-o', '--pass_through_options', dest='pass_through_options_encoded', action='append', type="string", help='These options are passed through directly to GATK, with decoding from binascii.unhexlify.' )
    parser.add_option( '-d', '--dataset', dest='datasets', action='append', type="string", nargs=4, help='"-argument" "original_filename" "galaxy_filetype" "name_prefix"' )
    parser.add_option( '', '--max_jvm_heap', dest='max_jvm_heap', action='store', type="string", default=None, help='If specified, the maximum java virtual machine heap size will be set to the provide value.' )
    parser.add_option( '', '--max_jvm_heap_fraction', dest='max_jvm_heap_fraction', action='store', type="int", default=None, help='If specified, the maximum java virtual machine heap size will be set to the provide value as a fraction of total physical memory.' )
    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )
    parser.add_option( '', '--html_report_from_directory', dest='html_report_from_directory', action='append', type="string", nargs=2, help='"Target HTML File" "Directory"')
    (options, args) = parser.parse_args()
    
    tmp_dir = tempfile.mkdtemp( prefix='tmp-gatk-' )
    if options.pass_through_options:
        cmd = ' '.join( options.pass_through_options )
    else:
        cmd = ''
    if options.pass_through_options_encoded:
        cmd = '%s %s' % ( cmd, ' '.join( map( unhexlify, options.pass_through_options_encoded ) ) )
    if options.max_jvm_heap is not None:
        cmd = cmd.replace( 'java ', 'java -Xmx%s ' % ( options.max_jvm_heap ), 1 )
    elif options.max_jvm_heap_fraction is not None:
        cmd = cmd.replace( 'java ', 'java -XX:DefaultMaxRAMFraction=%s  -XX:+UseParallelGC ' % ( options.max_jvm_heap_fraction ), 1 )
    bam_filenames = []
    if options.datasets:
        for ( dataset_arg, filename, galaxy_ext, prefix ) in options.datasets:
            gatk_filename = gatk_filename_from_galaxy( filename, galaxy_ext, target_dir = tmp_dir, prefix = prefix )
            if dataset_arg:
                cmd = '%s %s "%s"' % ( cmd, gatk_filetype_argument_substitution( dataset_arg, galaxy_ext ), gatk_filename )
            if galaxy_ext == "bam":
                bam_filenames.append( gatk_filename )
    index_bam_files( bam_filenames, tmp_dir )
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( prefix="gatk-stderr-", dir=tmp_dir )
    
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
    #generate html reports
    if options.html_report_from_directory:
        for ( html_filename, html_dir ) in options.html_report_from_directory:
            html_report_from_directory( open( html_filename, 'wb' ), html_dir )
    
    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
