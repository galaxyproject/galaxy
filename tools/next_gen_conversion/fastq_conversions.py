#!/usr/bin/env python

"""
Performs various conversions around Sanger FASTQ data

usage: %prog [options]
   -c, --command=c: Command to run
   -i, --input=i: Input file to be converted
   -o, --outputFastqsanger=o: FASTQ Sanger converted output file for sol2std
   -s, --outputFastqsolexa=s: FASTQ Solexa converted output file
   -f, --outputFasta=f: FASTA converted output file

usage: %prog command input_file output_file
"""

import os
import sys

from bx.cookbook import doc_optparse


def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()


def __main__():
    # Parse Command Line
    options, args = doc_optparse.parse( __doc__ )

    cmd = "fq_all2std.pl %s %s > %s"
    if options.command == 'sol2std':
        cmd = cmd % (options.command, options.input, options.outputFastqsanger)
    elif options.command == 'std2sol':
        cmd = cmd % (options.command, options.input, options.outputFastqsolexa)
    elif options.command == 'fq2fa':
        cmd = cmd % (options.command, options.input, options.outputFasta)
    try:
        os.system(cmd)
    except Exception as eq:
        stop_err("Error converting data format.\n" + str(eq))


if __name__ == "__main__":
    __main__()
