#!/usr/bin/env python
"""
This script will retrieve a list of dictionaries (one for each user) from the Tool Shed defined
by the --from_tool_shed parameter, which should be a base Tool Shed URL.  It will retrieve the
username from each dictionary and create a new user with that username in the Tool Shed defined
by the --to_tool_shed parameter (a different base Tool Shed URL).  An email and password value
will automatically be provided for each user.  Email addresses will be <username>@test.org and
passwords will be testuser.  Users that already exist with a specified username in the Tool Shed
in which the users are being created will not be affected.

This script is very useful for populating a new development Tool Shed with the set of users that
currently exist in either the test or main public Galaxy Tool Sheds.  This will streamline building
new repository hierarchies in the development Tool Shed and exporting them into a capsule that can
be imported into one of the public Tool Sheds.

Here is a working example of how to use this script to retrieve the current set of users that
are available in the test public Tool Shed and create each of them in a local development Tool Shed.

./create_users.py -a <api key> -f http://testtoolshed.g2.bx.psu.edu -t http://localhost:9009
"""

import os
import sys
import argparse
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import get
from common import submit

def main( options ):
    api_key = options.api
    from_tool_shed = options.from_tool_shed.rstrip( '/' )
    to_tool_shed = options.to_tool_shed.rstrip( '/' )
    # Get the users from the specified Tool Shed.
    url = '%s/api/users' % from_tool_shed
    user_dicts = get( url )
    create_response_dicts = []
    for user_dict in user_dicts:
        username = user_dict.get( 'username', None )
        if username is not None:
            email = '%s@test.org' % username
            password = 'testuser'
            data = dict( email=email,
                         password=password,
                         username=username )
            url = '%s/api/users' % to_tool_shed
            try:
                response = submit( url, data, api_key )
            except Exception, e:
                response = str( e )
                print "Error attempting to create user using URL: ", url, " exception: ", str( e )
            create_response_dict = dict( response=response )
            create_response_dicts.append( create_response_dict )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Retrieve a list of users from a Tool Shed and create them in another Tool Shed.' )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key for Tool Shed in which users will be created" )
    parser.add_argument( "-f", "--from_tool_shed", dest="from_tool_shed", required=True, help="URL of Tool Shed from which to retrieve the users" )
    parser.add_argument( "-t", "--to_tool_shed", dest="to_tool_shed", required=True, help="URL of Tool Shed in which to create the users" )
    options = parser.parse_args()
    main( options )
