#!/usr/bin/env python
"""
Script to reset metadata on certain repositories in the Tool Shed.  If the received API key is associated
with an admin user in the Tool Shed, setting the my_writable param value to True will restrict resetting
metadata to only repositories that are writable by the user in addition to those repositories of type
tool_dependency_definition.  The my_writable param is ignored if the current user is not an admin user,
in which case this same restriction is automatic.

usage: reset_metadata_on_repositories.py key <my_writable>

Here is a working example of how to use this script to reset metadata on certain repositories in a specified Tool Shed.
python ./reset_metadata_on_repositories.py -a 22be3b -m True -u http://localhost:9009/
"""

import argparse
import os
import sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import get
from common import submit

def string_as_bool( string ):
    if str( string ).lower() in [ 'true' ]:
        return True
    else:
        return False

def read_skip_file( skip_file ):
    encoded_ids_to_skip = []
    if os.path.exists( skip_file ):
        # Contents of file must be 1 encoded repository id per line.
        lines = open( skip_file, 'rb' ).readlines()
        for line in lines:
            if line.startswith( '#' ):
                # Skip comments.
                continue
            encoded_ids_to_skip.append( line.rstrip( '\n' ) )
    return encoded_ids_to_skip
    
def main( options ):
    api_key = options.api
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    my_writable = options.my_writable
    one_per_request = options.one_per_request
    skip_file = options.skip_file
    if skip_file:
        encoded_ids_to_skip = read_skip_file( skip_file )
    else:
        encoded_ids_to_skip = []
    if string_as_bool( one_per_request ):
        url = '%s/api/repositories/repository_ids_for_setting_metadata?key=%s&my_writable=%s' % ( base_tool_shed_url, api_key, str( my_writable ) )
        repository_ids = get( url, api_key )
        for repository_id in repository_ids:
            if repository_id in encoded_ids_to_skip:
                print "--------"
                print "Skipping repository with id %s because it is in skip file %s" % ( str( repository_id ), str( skip_file ) )
                print "--------"
            else:
                data = dict( repository_id=repository_id )
                url = '%s/api/repositories/reset_metadata_on_repository' % base_tool_shed_url
                try:
                    submit( url, data, options.api )
                except Exception, e:
                    log.exception( ">>>>>>>>>>>>>>>Blew up on data: %s, exception: %s" % ( str( data ), str( e ) ) )
                    # An nginx timeout undoubtedly occurred.
                    sys.exit( 1 )
    else:
        data = dict( encoded_ids_to_skip=encoded_ids_to_skip,
                     my_writable=my_writable )
        url = '%s/api/repositories/reset_metadata_on_repositories' % base_tool_shed_url
        try:
            submit( url, data, options.api )
        except Exception, e:
            log.exception( str( e ) )
            # An nginx timeout undoubtedly occurred.
            sys.exit( 1 )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Reset metadata on certain repositories in the Tool Shed via the Tool Shed API.' )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )
    parser.add_argument( "-m", "--my_writable", dest="my_writable", required=False, default='False', help="Restrict to my writable repositories" )
    parser.add_argument( "-o", "--one_per_request", dest="one_per_request", required=False, default='True', help="One repository per request" )
    parser.add_argument( "-s", "--skip_file", dest="skip_file", required=False, help="Name of local file containing encoded repository ids to skip" )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    options = parser.parse_args()
    main( options )
