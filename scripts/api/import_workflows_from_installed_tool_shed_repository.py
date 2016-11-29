#!/usr/bin/env python
"""
Import one or more exported workflows contained within a specified tool shed repository installed into Galaxy.

Here is a working example of how to use this script to repair a repository installed into Galaxy.
python ./import_workflows_from_installed_tool_shed_repository.py -a 22be3b -l http://localhost:8763/ -n workflow_with_tools -o test -r ef45bb64237e -u http://localhost:9009/
"""
from __future__ import print_function

import argparse

from common import display, submit


def clean_url( url ):
    if url.find( '//' ) > 0:
        # We have an url that includes a protocol, something like: http://localhost:9009
        items = url.split( '//' )
        return items[ 1 ].rstrip( '/' )
    return url.rstrip( '/' )


def main( options ):
    api_key = options.api
    base_galaxy_url = options.local_url.rstrip( '/' )
    base_tool_shed_url = options.tool_shed_url.rstrip( '/' )
    cleaned_tool_shed_url = clean_url( base_tool_shed_url )
    installed_tool_shed_repositories_url = '%s/api/tool_shed_repositories' % base_galaxy_url
    tool_shed_repository_id = None
    installed_tool_shed_repositories = display( api_key, installed_tool_shed_repositories_url, return_formatted=False )
    for installed_tool_shed_repository in installed_tool_shed_repositories:
        tool_shed = str( installed_tool_shed_repository[ 'tool_shed' ] )
        name = str( installed_tool_shed_repository[ 'name' ] )
        owner = str( installed_tool_shed_repository[ 'owner' ] )
        changeset_revision = str( installed_tool_shed_repository[ 'changeset_revision' ] )
        if tool_shed == cleaned_tool_shed_url and name == options.name and owner == options.owner and changeset_revision == options.changeset_revision:
            tool_shed_repository_id = installed_tool_shed_repository[ 'id' ]
            break
    if tool_shed_repository_id:
        # Get the list of exported workflows contained in the installed repository.
        url = '%s%s' % ( base_galaxy_url, '/api/tool_shed_repositories/%s/exported_workflows' % str( tool_shed_repository_id ) )
        exported_workflows = display( api_key, url, return_formatted=False )
        if exported_workflows:
            # Import all of the workflows in the list of exported workflows.
            data = {}
            # NOTE: to import a single workflow, add an index to data (e.g.,
            # data[ 'index' ] = 0
            # and change the url to be ~/import_workflow (singular).  For example,
            # url = '%s%s' % ( base_galaxy_url, '/api/tool_shed_repositories/%s/import_workflow' % str( tool_shed_repository_id ) )
            url = '%s%s' % ( base_galaxy_url, '/api/tool_shed_repositories/%s/import_workflows' % str( tool_shed_repository_id ) )
            submit( options.api, url, data )
    else:
        print("Invalid tool_shed / name / owner / changeset_revision.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Import workflows contained in an installed tool shed repository via the Galaxy API.' )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-l", "--local", dest="local_url", required=True, help="URL of the galaxy instance." )
    parser.add_argument( "-n", "--name", required=True, help="Repository name." )
    parser.add_argument( "-o", "--owner", required=True, help="Repository owner." )
    parser.add_argument( "-r", "--revision", dest="changeset_revision", required=True, help="Repository owner." )
    options = parser.parse_args()
    main( options )
