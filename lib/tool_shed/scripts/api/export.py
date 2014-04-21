#!/usr/bin/env python
"""
Export a specified repository revision and optionally all of its defined repository dependencies from the tool shed into a compressed archive.

Here is a working example of how to use this script to export a repository from the tool shed.
./export.py --url http://testtoolshed.g2.bx.psu.edu --name chemicaltoolbox --owner bgruening --revision 4133dbf7ff4d --export_repository_dependencies True --download_dir /tmp
"""

import os
import sys
import argparse
import urllib2
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import display
from common import submit
from tool_shed.util import export_util

CHUNK_SIZE = 2**20 # 1Mb

def get_file_type_str( changeset_revision, file_type ):
    if file_type == 'zip':
        file_type_str = '%s.zip' % changeset_revision
    elif file_type == 'bz2':
        file_type_str = '%s.tar.bz2' % changeset_revision
    elif file_type == 'gz':
        file_type_str = '%s.tar.gz' % changeset_revision
    else:
        file_type_str = ''
    return file_type_str

def string_as_bool( string ):
    if str( string ).lower() in ( 'true', 'yes', 'on' ):
        return True
    else:
        return False

def main( options ):
    """Collect all user data and export the repository via the Tool Shed API."""
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    repositories_url = '%s/api/repositories' % base_tool_shed_url
    data = {}
    data[ 'tool_shed_url' ] = base_tool_shed_url
    data[ 'name' ] = options.name
    data[ 'owner' ] = options.owner
    data[ 'changeset_revision' ] = options.changeset_revision
    data[ 'export_repository_dependencies' ] = options.export_repository_dependencies
    repository_id = None
    repositories = display( repositories_url, api_key=None, return_formatted=False )
    for repository in repositories:
        name = str( repository[ 'name' ] )
        owner = str( repository[ 'owner' ] )
        if name == options.name and owner == options.owner:
            repository_id = repository[ 'id' ]
            break
    if repository_id:
        # We'll currently support only gzip-compressed tar archives.
        file_type = 'gz'
        url = '%s%s' % ( base_tool_shed_url, '/api/repository_revisions/%s/export' % str( repository_id ) )
        export_dict = submit( url, data, return_formatted=False )
        error_messages = export_dict[ 'error_messages' ]
        if error_messages:
            print "Error attempting to export revision ", options.changeset_revision, " of repository ", options.name, " owned by ", options.owner, ":\n", error_messages
        else:
            repositories_archive_filename = \
                export_util.generate_repository_archive_filename( base_tool_shed_url,
                                                                  options.name,
                                                                  options.owner,
                                                                  options.changeset_revision,
                                                                  file_type,
                                                                  export_repository_dependencies=string_as_bool( options.export_repository_dependencies ),
                                                                  use_tmp_archive_dir=False )
            download_url = export_dict[ 'download_url' ]
            download_dir = os.path.abspath( options.download_dir )
            file_path = os.path.join( download_dir, repositories_archive_filename )
            src = None
            dst = None
            try:
                src = urllib2.urlopen( download_url )
                dst = open( file_path, 'wb' )
                while True:
                    chunk = src.read( CHUNK_SIZE )
                    if chunk:
                        dst.write( chunk )
                    else:
                        break
            except:
                raise
            finally:
                if src:
                    src.close()
                if dst:
                    dst.close()
            print "Successfully exported revision ", options.changeset_revision, " of repository ", options.name, " owned by ", options.owner
            print "to location ", file_path
    else:
        print "Invalid tool_shed / name / owner ."

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Installation of tool shed repositories via the Galaxy API.' )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-n", "--name", required=True, help="Repository name." )
    parser.add_argument( "-o", "--owner", required=True, help="Repository owner." )
    parser.add_argument( "-r", "--revision", dest="changeset_revision", required=True, help="Repository owner." )
    parser.add_argument( "-e", "--export_repository_dependencies", dest="export_repository_dependencies", required=False, default='False', help="Export repository dependencies." )
    parser.add_argument( "-d", "--download_dir", dest="download_dir", required=False, default='/tmp', help="Download directory." )
    options = parser.parse_args()
    main( options )
