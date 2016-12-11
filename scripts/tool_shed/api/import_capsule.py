#!/usr/bin/env python
"""
Import the contents of a repository capsule exported from a Tool Shed into another Tool Shed.  For each exported repository
archive contained in the capsule, inspect the Tool Shed to see if that repository already exists or if the current user is
authorized to create the repository.  If repository dependencies are included in the capsule, repositories may have various
owners.  We will keep repositories associated with owners, so we need to restrict created repositories to those the current
user can create.  If the current user is an admin or a member of the IUC, all repositories will be created no matter the owner.
Otherwise, only repositories whose associated owner is the current user will be created.

Repositories are also associated with 1 or more categories in the Tool Shed from which the capsule was exported.  If any of
these categories are not contained in the Tool Shed to which the capsule is being imported, they will NOT be created by this
method (they'll have to be created manually, which can be done after the import).

Here is a working example of how to use this script to install a repository from the test tool shed.
./import_capsule.py -a <api key> -u http://localhost:9009 -c capsule_localhost_colon_9009_filter_test1_8923f52d5c6d.tar.gz
"""
import argparse
import logging
import sys

from common import submit

log = logging.getLogger(__name__)


def main( options ):
    api_key = options.api
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    data = {}
    data[ 'tool_shed_url' ] = options.tool_shed_url
    data[ 'capsule_file_name' ] = options.capsule_file_name
    url = '%s/api/repositories/new/import_capsule' % base_tool_shed_url
    try:
        submit( url, data, api_key )
    except Exception as e:
        log.exception( str( e ) )
        sys.exit( 1 )


if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Import the contents of a repository capsule via the Tool Shed API.' )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )
    parser.add_argument( "-c", "--capsule_file_name", required=True, help="Capsule file name." )
    options = parser.parse_args()
    main( options )
