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
from common import submit

def main( options ):
    api_key = options.api
    my_writable = options.my_writable
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    data = dict( my_writable=my_writable )
    url = '%s/api/repositories/reset_metadata_on_repositories' % base_tool_shed_url
    submit( url, data, options.api )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Reset metadata on certain repositories in the Tool Shed via the Tool Shed API.' )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )
    parser.add_argument( "-m", "--my_writable", dest="my_writable", required=False, default='False', help="Restrict to my writable repositories" )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    options = parser.parse_args()
    main( options )
