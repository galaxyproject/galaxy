#!/usr/bin/env python
# Dan Blankenberg

"""
A wrapper script for converting SAM to BAM, with sorting.
%prog input_filename.sam output_filename.bam
"""
import os
import sys
import optparse
import tempfile
import subprocess
import shutil
from distutils.version import LooseVersion

CHUNK_SIZE = 2 ** 20  # 1mb


def cleanup_before_exit( tmp_dir ):
    if tmp_dir and os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )


def cmd_exists(cmd):
    # http://stackoverflow.com/questions/5226958/which-equivalent-function-in-python
    for path in os.environ["PATH"].split(":"):
        if os.path.exists(os.path.join(path, cmd)):
            return True
    return False


def _get_samtools_version():
    version = '0.0.0'
    if not cmd_exists('samtools'):
        raise Exception('This tool needs samtools, but it is not on PATH.')
    # Get the version of samtools via --version-only, if available
    p = subprocess.Popen( ['samtools', '--version-only'],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    output, error = p.communicate()

    # --version-only is available
    # Format is <version x.y.z>+htslib-<a.b.c>
    if p.returncode == 0:
        version = output.split('+')[0]
        return version

    output = subprocess.Popen( [ 'samtools' ], stderr=subprocess.PIPE, stdout=subprocess.PIPE ).communicate()[1]
    lines = output.split( '\n' )
    for line in lines:
        if line.lower().startswith( 'version' ):
            # Assuming line looks something like: version: 0.1.12a (r862)
            version = line.split()[1]
            break
    return version


def __main__():
    # Parse Command Line
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()

    assert len( args ) == 2, 'You must specify the input and output filenames'
    input_filename, output_filename = args

    tmp_dir = tempfile.mkdtemp( prefix='tmp-sam_to_bam_converter-' )

    # convert to SAM
    unsorted_bam_filename = os.path.join( tmp_dir, 'unsorted.bam' )
    unsorted_stderr_filename = os.path.join( tmp_dir, 'unsorted.stderr' )
    cmd = "samtools view -bS '%s' > '%s'" % ( input_filename, unsorted_bam_filename )
    proc = subprocess.Popen( args=cmd, stderr=open( unsorted_stderr_filename, 'wb' ), shell=True, cwd=tmp_dir )
    return_code = proc.wait()
    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    stderr = open( unsorted_stderr_filename )
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()

    # sort sam, so indexing will not fail
    sorted_stderr_filename = os.path.join( tmp_dir, 'sorted.stderr' )
    sorting_prefix = os.path.join( tmp_dir, 'sorted_bam' )
    # samtools changed sort command arguments (starting from version 1.3)
    samtools_version = LooseVersion(_get_samtools_version())
    if samtools_version < LooseVersion('1.0'):
        cmd = "samtools sort -o '%s' '%s' > '%s'" % ( unsorted_bam_filename, sorting_prefix, output_filename )
    else:
        cmd = "samtools sort -T '%s' '%s' > '%s'" % ( sorting_prefix, unsorted_bam_filename, output_filename )
    proc = subprocess.Popen( args=cmd, stderr=open( sorted_stderr_filename, 'wb' ), shell=True, cwd=tmp_dir )
    return_code = proc.wait()

    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    stderr = open( sorted_stderr_filename )
    while True:
        chunk = stderr.read( CHUNK_SIZE )
        if chunk:
            stderr_target.write( chunk )
        else:
            break
    stderr.close()

    cleanup_before_exit( tmp_dir )


if __name__ == "__main__":
    __main__()
