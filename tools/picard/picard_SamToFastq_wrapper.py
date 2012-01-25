#!/usr/bin/env python
#Dan Blankenberg

"""
A wrapper script for running the Picard SamToFastq command. Allows parsing read groups into separate files.
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
    parser.add_option( '-p', '--pass_through', dest='pass_through_options', action='append', type="string", help='These options are passed through directly to PICARD, without any modification.' )
    parser.add_option( '-1', '--read_group_file_1', dest='read_group_file_1', action='store', type="string", default=None, help='Read Group 1 output file, when using multiple readgroups' )
    parser.add_option( '-2', '--read_group_file_2', dest='read_group_file_2', action='store', type="string", default=None, help='Read Group 2 output file, when using multiple readgroups and paired end' )
    parser.add_option( '', '--stdout', dest='stdout', action='store', type="string", default=None, help='If specified, the output of stdout will be written to this file.' )
    parser.add_option( '', '--stderr', dest='stderr', action='store', type="string", default=None, help='If specified, the output of stderr will be written to this file.' )
    parser.add_option( '-n', '--new_files_path', dest='new_files_path', action='store', type="string", default=None, help='new_files_path')
    parser.add_option( '-i', '--file_id_1', dest='file_id_1', action='store', type="string", default=None, help='file_id_1')
    parser.add_option( '-f', '--file_id_2', dest='file_id_2', action='store', type="string", default=None, help='file_id_2')
    (options, args) = parser.parse_args()
    
    tmp_dir = tempfile.mkdtemp( prefix='tmp-picard-' )
    if options.pass_through_options:
        cmd = ' '.join( options.pass_through_options )
    else:
        cmd = ''
    if options.new_files_path is not None:
        print 'Creating FASTQ files by Read Group'
        assert None not in [ options.read_group_file_1, options.new_files_path, options.file_id_1 ], 'When using read group aware, you need to specify --read_group_file_1, --read_group_file_2 (when paired end), --new_files_path, and --file_id'
        cmd = '%s OUTPUT_DIR="%s"' % ( cmd,  tmp_dir)
    #set up stdout and stderr output options
    stdout = open_file_from_option( options.stdout, mode = 'wb' )
    if stdout is None:
        stdout = sys.stdout
    stderr = open_file_from_option( options.stderr, mode = 'wb' )
    #if no stderr file is specified, we'll use our own
    if stderr is None:
        stderr = tempfile.NamedTemporaryFile( prefix="picard-stderr-", dir=tmp_dir )
    
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
    #if rg aware, put files where they belong
    if options.new_files_path is not None:
        fastq_1_name = options.read_group_file_1
        fastq_2_name = options.read_group_file_2
        file_id_1 = options.file_id_1
        file_id_2 = options.file_id_2
        if file_id_2 is None:
            file_id_2 = file_id_1
        for filename in sorted( os.listdir( tmp_dir ) ):
            if filename.endswith( '_1.fastq' ):
                if fastq_1_name:
                    shutil.move( os.path.join( tmp_dir, filename ), fastq_1_name )
                    fastq_1_name = None
                else:
                    shutil.move( os.path.join( tmp_dir, filename ), os.path.join( options.new_files_path, 'primary_%s_%s - 1_visible_fastqsanger' % ( file_id_1, filename[:-len( '_1.fastq' )] ) ) )
            elif filename.endswith( '_2.fastq' ):
                if fastq_2_name:
                    shutil.move( os.path.join( tmp_dir, filename ), fastq_2_name )
                    fastq_2_name = None
                else:
                    shutil.move( os.path.join( tmp_dir, filename ), os.path.join( options.new_files_path, 'primary_%s_%s - 2_visible_fastqsanger' % ( file_id_2, filename[:-len( '_2.fastq' )] ) ) )
    
    cleanup_before_exit( tmp_dir )

if __name__=="__main__": __main__()
