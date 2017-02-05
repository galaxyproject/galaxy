#!/usr/bin/env python

"""
Uses pysam to bgzip a file

usage: %prog in_file out_file
"""
import optparse
import subprocess
import tempfile

from pysam import ctabix


def main():
    # Read options, args.
    parser = optparse.OptionParser()
    parser.add_option( '-c', '--chr-col', type='int', dest='chrom_col' )
    parser.add_option( '-s', '--start-col', type='int', dest='start_col' )
    parser.add_option( '-e', '--end-col', type='int', dest='end_col' )
    parser.add_option( '-P', '--preset', dest='preset' )
    (options, args) = parser.parse_args()
    input_fname, output_fname = args

    tmpfile = tempfile.NamedTemporaryFile()
    sort_params = None

    if options.chrom_col and options.start_col and options.end_col:
        sort_params = [
            "sort",
            "-k%(i)s,%(i)s" % { 'i': options.chrom_col },
            "-k%(i)i,%(i)in" % { 'i': options.start_col },
            "-k%(i)i,%(i)in" % { 'i': options.end_col }
        ]
    elif options.preset == "bed":
        sort_params = ["sort", "-k1,1", "-k2,2n", "-k3,3n"]
    elif options.preset == "vcf":
        sort_params = ["sort", "-k1,1", "-k2,2n"]
    elif options.preset == "gff":
        sort_params = ["sort", "-s", "-k1,1", "-k4,4n"]  # stable sort on start column
    # Skip any lines starting with "#" and "track"
    grepped = subprocess.Popen(["grep", "-e", "^\"#\"", "-e", "^track", "-v", input_fname], stderr=subprocess.PIPE, stdout=subprocess.PIPE )
    after_sort = subprocess.Popen(sort_params, stdin=grepped.stdout, stderr=subprocess.PIPE, stdout=tmpfile )
    grepped.stdout.close()
    output, err = after_sort.communicate()

    ctabix.tabix_compress(tmpfile.name, output_fname, force=True)


if __name__ == "__main__":
    main()
