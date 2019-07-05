#!/usr/bin/env python
# Dan Blankenberg

"""
A wrapper script for converting SAM to BAM, with sorting.
%prog input_filename.sam output_filename.bam
"""
import optparse
import os
import shutil
import subprocess
import sys
import tempfile

import packaging.version

CHUNK_SIZE = 2 ** 20  # 1mb


def cleanup_before_exit(tmp_dir):
    if tmp_dir and os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


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
    p = subprocess.Popen(['samtools', '--version-only'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    # --version-only is available
    # Format is <version x.y.z>+htslib-<a.b.c>
    if p.returncode == 0:
        version = output.split('+')[0]
        return version

    output = subprocess.Popen(['samtools'], stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[1]
    lines = output.split('\n')
    for line in lines:
        if line.lower().startswith('version'):
            # Assuming line looks something like: version: 0.1.12a (r862)
            version = line.split()[1]
            break
    return version


def __main__():
    # Parse Command Line
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()

    assert len(args) == 2, 'You must specify the input and output filenames'
    input_filename, output_filename = args

    tmp_dir = tempfile.mkdtemp(prefix='tmp-sam_to_bam_converter-')

    # convert to SAM
    unsorted_bam_filename = os.path.join(tmp_dir, 'unsorted.bam')
    unsorted_stderr_filename = os.path.join(tmp_dir, 'unsorted.stderr')
    proc = subprocess.Popen(['samtools', 'view', '-bS', input_filename],
                            stdout=open(unsorted_bam_filename, 'wb'),
                            stderr=open(unsorted_stderr_filename, 'wb'),
                            cwd=tmp_dir)
    return_code = proc.wait()
    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    with open(unsorted_stderr_filename) as stderr:
        while True:
            chunk = stderr.read(CHUNK_SIZE)
            if chunk:
                stderr_target.write(chunk)
            else:
                break

    # sort sam, so indexing will not fail
    sorted_stderr_filename = os.path.join(tmp_dir, 'sorted.stderr')
    sorting_prefix = os.path.join(tmp_dir, 'sorted_bam')
    # samtools changed sort command arguments (starting from version 1.3)
    samtools_version = packaging.version.parse(_get_samtools_version())
    if samtools_version < packaging.version.parse('1.0'):
        sort_args = ['-o', unsorted_bam_filename, sorting_prefix]
    else:
        sort_args = ['-T', sorting_prefix, unsorted_bam_filename]
    proc = subprocess.Popen(['samtools', 'sort'] + sort_args,
                            stdout=open(output_filename, 'wb'),
                            stderr=open(sorted_stderr_filename, 'wb'),
                            cwd=tmp_dir)
    return_code = proc.wait()

    if return_code:
        stderr_target = sys.stderr
    else:
        stderr_target = sys.stdout
    with open(sorted_stderr_filename) as stderr:
        while True:
            chunk = stderr.read(CHUNK_SIZE)
            if chunk:
                stderr_target.write(chunk)
            else:
                break

    cleanup_before_exit(tmp_dir)


if __name__ == "__main__":
    __main__()
