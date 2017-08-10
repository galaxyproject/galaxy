#!/usr/bin/env python
"""
Add appropriate entries to the Tool Shed's repository registry for a specified repository.

Here is a working example of how to use this script.
python ./add_repository_registry_entry.py -a <api key> -u <tool shed url> -n <repository name> -o <repository owner>
"""

import argparse

from common import submit


def main( options ):
    api_key = options.api_key
    if api_key:
        if options.tool_shed_url and options.name and options.owner:
            base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
            data = {}
            data[ 'tool_shed_url' ] = base_tool_shed_url
            data[ 'name' ] = options.name
            data[ 'owner' ] = options.owner
            url = '%s%s' % ( base_tool_shed_url, '/api/repositories/add_repository_registry_entry' )
            response_dict = submit( url, data, api_key=api_key, return_formatted=False )
            print response_dict
        else:
            print "Invalid tool_shed: ", base_tool_shed_url, " name: ", options.name, " or owner: ", options.owner, "."
    else:
        print "An API key for an admin user in the Tool Shed is required to add entries into the Tool Shed's repository registry."


if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Add entries into the Tool Shed repository registry for a specified repository.' )
    parser.add_argument( "-a", "--api_key", dest="api_key", required=True, help="API Key for user adding entries into the Tool Shed's repository registry." )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-n", "--name", dest='name', required=True, help="Repository name." )
    parser.add_argument( "-o", "--owner", dest='owner', required=True, help="Repository owner." )
    options = parser.parse_args()
    main( options )
