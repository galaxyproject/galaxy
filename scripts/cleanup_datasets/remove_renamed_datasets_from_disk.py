#!/usr/bin/env python
"""
Removes a dataset file ( which was first renamed by appending _purged to the file name ) from disk.
Usage: python remove_renamed_datasets_from_disk.py renamed.log
"""

import sys, os

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    infile = sys.argv[1]
    outfile = infile + ".removed.log"
    out = open( outfile, 'w' )
    
    print >> out, "# The following renamed datasets have been removed from disk"
    i = 0
    removed_files = 0
    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if line and line.startswith( '/var/opt/galaxy' ):
            try:
                os.unlink( line )
                print >> out, line
                removed_files += 1
            except Exception, exc:
                print >> out, "# Error, exception " + str( exc ) + " caught attempting to remove " + line
    print >> out, "# Removed " + str( removed_files ) + " files"    

if __name__ == "__main__":
    main()
