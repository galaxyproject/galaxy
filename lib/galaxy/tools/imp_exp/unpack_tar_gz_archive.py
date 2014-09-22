#!/usr/bin/env python
"""
Unpack a tar or tar.gz archive into a directory.

usage: %prog archive_source dest_dir
    --[url|file] source type, either a URL or a file.
"""

import sys
import optparse
import tarfile
import tempfile
import urllib2
import math
from base64 import b64decode

# Set max size of archive/file that will be handled to be 100 GB. This is
# arbitrary and should be adjusted as needed.
MAX_SIZE = 100 * math.pow( 2, 30 )


def url_to_file( url, dest_file ):
    """
    Transfer a file from a remote URL to a temporary file.
    """
    try:
        url_reader = urllib2.urlopen( url )
        CHUNK = 10 * 1024  # 10k
        total = 0
        fp = open( dest_file, 'wb')
        while True:
            chunk = url_reader.read( CHUNK )
            if not chunk:
                break
            fp.write( chunk )
            total += CHUNK
            if total > MAX_SIZE:
                break
        fp.close()
        return dest_file
    except Exception, e:
        print "Exception getting file from URL: %s" % e, sys.stderr
        return None


def unpack_archive( archive_file, dest_dir ):
    """
    Unpack a tar and/or gzipped archive into a destination directory.
    """
    archive_fp = tarfile.open( archive_file, mode='r:gz' )
    archive_fp.extractall( path=dest_dir )
    archive_fp.close()

if __name__ == "__main__":
    # Parse command line.
    parser = optparse.OptionParser()
    parser.add_option( '-U', '--url', dest='is_url', action="store_true", help='Source is a URL.' )
    parser.add_option( '-F', '--file', dest='is_file', action="store_true", help='Source is a URL.' )
    parser.add_option( '-e', '--encoded', dest='is_b64encoded', action="store_true", default=False, help='Source and destination dir values are base64 encoded.' )
    (options, args) = parser.parse_args()
    is_url = bool( options.is_url )
    is_file = bool( options.is_file )
    archive_source, dest_dir = args

    if options.is_b64encoded:
        archive_source = b64decode( archive_source )
        dest_dir = b64decode( dest_dir )

    try:
        # Get archive from URL.
        if is_url:
            archive_file = url_to_file( archive_source, tempfile.NamedTemporaryFile( dir=dest_dir ).name )
        elif is_file:
            archive_file = archive_source

        # Unpack archive.
        unpack_archive( archive_file, dest_dir )
    except Exception, e:
        print "Error unpacking tar/gz archive: %s" % e, sys.stderr
