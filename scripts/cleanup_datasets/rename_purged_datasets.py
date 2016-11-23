#!/usr/bin/env python
"""
Renames a dataset file by appending _purged to the file name so that it can later be removed from disk.
Usage: python rename_purged_datasets.py purge.log
"""
from __future__ import print_function

import os
import sys

assert sys.version_info[:2] >= ( 2, 4 )


def usage(prog):
    print("usage: %s file" % prog)
    print("""
Marks a set of files as purged and renames them. The input file should contain a
list of files to be purged, one per line. The full path must be specified and
must begin with /var/opt/galaxy.
A log of files marked as purged is created in a file with the same name as that
input but with _purged appended. The resulting files can finally be removed from
disk with remove_renamed_datasets_from_disk.py, by supplying it with a list of
them.
    """)


def main():
    if len(sys.argv) != 2 or sys.argv == "-h" or sys.argv == "--help":
        usage(sys.argv[0])
        sys.exit()
    infile = sys.argv[1]
    outfile = infile + ".renamed.log"
    out = open( outfile, 'w' )

    print("# The following renamed datasets can be removed from disk", file=out)
    i = 0
    renamed_files = 0
    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if line and line.startswith( '/var/opt/galaxy' ):
            try:
                purged_filename = line + "_purged"
                os.rename( line, purged_filename )
                print(purged_filename, file=out)
                renamed_files += 1
            except Exception as exc:
                print("# Error, exception " + str( exc ) + " caught attempting to rename " + purged_filename, file=out)
    print("# Renamed " + str( renamed_files ) + " files", file=out)


if __name__ == "__main__":
    main()
