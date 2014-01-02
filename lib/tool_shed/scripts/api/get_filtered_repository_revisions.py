#!/usr/bin/env python
"""
Get a list of dictionaries, each of which defines a repository revision, that is filtered by a combination of one or more
of the following.

- do_not_test : true / false
- downloadable : true / false
- includes_tools : true / false
- malicious : true / false
- missing_test_components : true / false
- skip_tool_test : true / false
- test_install_error : true / false
- tools_functionally_correct : true / false

Results can also be restricted to the latest downloadable revision of each repository.

This script is useful for analyzing the Tool Shed's install and test framework.

Here is a working example of how to use this script.
./get_filtered_repository_revisions.py --url http://testtoolshed.g2.bx.psu.edu 
"""

import argparse
import os
import sys
import urllib

sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import get
from galaxy.util.json import from_json_string
import tool_shed.util.shed_util_common as suc

def get_api_url( base, parts=[], params=None ):
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts:
        parts.insert( 0, 'api' )
    url = suc.url_join( base, *parts )
    if params:
        url += '?%s' % params
    return url

def get_latest_downloadable_changeset_revision( url, name, owner ):
    error_message = ''
    parts = [ 'api', 'repositories', 'get_ordered_installable_revisions' ]
    params = urllib.urlencode( dict( name=name, owner=owner ) )
    api_url = get_api_url( base=url, parts=parts, params=params )
    changeset_revisions, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    if changeset_revisions:
        return changeset_revisions[ -1 ], error_message
    else:
        return suc.INITIAL_CHANGELOG_HASH, error_message

def get_repository_dict( url, repository_dict ):
    error_message = ''
    parts = [ 'api', 'repositories', repository_dict[ 'repository_id' ] ]
    api_url = get_api_url( base=url, parts=parts )
    extended_dict, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    name = str( extended_dict[ 'name' ] )
    owner = str( extended_dict[ 'owner' ] )
    latest_changeset_revision, error_message = get_latest_downloadable_changeset_revision( url, name, owner )
    if error_message:
        print error_message
    extended_dict[ 'latest_revision' ] = str( latest_changeset_revision )
    return extended_dict, error_message

def json_from_url( url ):
    error_message = ''
    url_handle = urllib.urlopen( url )
    url_contents = url_handle.read()
    try:
        parsed_json = from_json_string( url_contents )
    except Exception, e:
        error_message = str( url_contents )
        return None, error_message
    return parsed_json, error_message

def string_as_bool( string ):
    if str( string ).lower() in [ 'true' ]:
        return True
    else:
        return False

def main( options ):
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    latest_revision_only = string_as_bool( options.latest_revision_only )
    do_not_test = str( options.do_not_test )
    downloadable = str( options.downloadable )
    includes_tools = str( options.includes_tools )
    malicious = str( options.malicious )
    missing_test_components = str( options.missing_test_components )
    skip_tool_test = str( options.skip_tool_test )
    test_install_error = str( options.test_install_error )
    tools_functionally_correct = str( options.tools_functionally_correct )
    parts=[ 'repository_revisions' ]
    params = urllib.urlencode( dict( do_not_test=do_not_test,
                                     downloadable=downloadable,
                                     includes_tools=includes_tools,
                                     malicious=malicious,
                                     missing_test_components=missing_test_components,
                                     skip_tool_test=skip_tool_test,
                                     test_install_error=test_install_error,
                                     tools_functionally_correct=tools_functionally_correct ) )
    api_url = get_api_url( base=base_tool_shed_url, parts=parts, params=params )
    baseline_repository_dicts, error_message = json_from_url( api_url )
    if error_message:
        print error_message
    repository_dicts = []
    for baseline_repository_dict in baseline_repository_dicts:
        # We need to get some details from the tool shed API, such as repository name and owner, to pass on to the
        # module that will generate the install methods.
        repository_dict, error_message = get_repository_dict( base_tool_shed_url, baseline_repository_dict )
        if error_message:
            print 'Error getting additional details from the API: ', error_message
            repository_dicts.append( baseline_repository_dict )
        else:
            # Don't test empty repositories.
            changeset_revision = baseline_repository_dict[ 'changeset_revision' ]
            if changeset_revision != suc.INITIAL_CHANGELOG_HASH:
                # Merge the dictionary returned from /api/repository_revisions with the detailed repository_dict and
                # append it to the list of repository_dicts to install and test.
                if latest_revision_only:
                    latest_revision = repository_dict[ 'latest_revision' ]
                    if changeset_revision == latest_revision:
                        repository_dicts.append( dict( repository_dict.items() + baseline_repository_dict.items() ) )
                else:
                    repository_dicts.append( dict( repository_dict.items() + baseline_repository_dict.items() ) )
    print '\n\n', repository_dicts
    print '\nThe url:\n\n', api_url, '\n\nreturned ', len( repository_dicts ), ' repository dictionaries...'

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Get a filtered list of repository dictionaries.' )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-l", "--latest_revision_only", dest="latest_revision_only", default=True,
                         help="Restrict results to latest downloadable revision only" )
    parser.add_argument( "-n", "--do_not_test", help="do_not_test", default=False )
    parser.add_argument( "-d", "--downloadable", help="downloadable", default=True )
    parser.add_argument( "-i", "--includes_tools", help="includes_tools", default=True )
    parser.add_argument( "-m", "--malicious", help="malicious", default=False )
    parser.add_argument( "-c", "--missing_test_components", help="missing_test_components", default=False )
    parser.add_argument( "-s", "--skip_tool_test", help="skip_tool_test", default=False )
    parser.add_argument( "-e", "--test_install_error", help="test_install_error", default=False )
    parser.add_argument( "-t", "--tools_functionally_correct", help="tools_functionally_correct", default=True )    
    options = parser.parse_args()
    main( options )
