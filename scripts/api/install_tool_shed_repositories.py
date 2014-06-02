#!/usr/bin/env python
"""
If a repository name, owner and revision are specified,install the revision from a specified tool shed into Galaxy.
Specifying a revision is optional, if it is no specified, the latest installable revision will automatically be installed.
However, the name and owner are required.

This example demonstrates installation of a repository that contains valid tools, loading them into a section of the
Galaxy tool panel or creating a new tool panel section.  You can choose if tool dependencies or repository dependencies
should be installed, use --repository-deps or --tool-deps.

This example requires a tool panel config file (e.g., tool_conf.xml, shed_tool_conf.xml, etc) to contain a tool panel section like the following:

<section id="from_test_tool_shed" name="From Test Tool Shed" version="">
</section>

Here is a working example of how to use this script to install a repository from the test tool shed.
./install_tool_shed_repositories.py --api <api key> --local <galaxy base url> --url http://testtoolshed.g2.bx.psu.edu --name gregs_filter --owner greg --tool-deps
"""

import os
import sys
import argparse
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

def main( options ):
    """Collect all user data and install the tools via the Galaxy API."""
    data = {}
    data[ 'tool_shed_url' ] = options.tool_shed_url
    data[ 'name' ] = options.name
    data[ 'owner' ] = options.owner
    if options.changeset_revision:
        data[ 'changeset_revision' ] = options.changeset_revision
    else:
        # If the changeset_revision is not specified, default to the latest installable revision.
        revision_data = {}
        revision_data[ 'tool_shed_url' ] = options.tool_shed_url.rstrip( '/' )
        revision_data[ 'name' ] = options.name
        revision_data[ 'owner' ] = options.owner
        revision_url = '%s%s' % ( options.local_url.rstrip( '/' ), '/api/tool_shed_repositories/get_latest_installable_revision' )
        latest_installable_revision = submit( options.api,
                                              revision_url,
                                              revision_data,
                                              return_formatted=False )
        data[ 'changeset_revision' ] = latest_installable_revision
    if options.tool_panel_section_id:
        data[ 'tool_panel_section_id' ] = options.tool_panel_section_id
    elif options.new_tool_panel_section_label:
        data[ 'new_tool_panel_section_label' ] = options.new_tool_panel_section_label
    if options.install_repository_dependencies:
        data[ 'install_repository_dependencies' ] = options.install_repository_dependencies
    if options.install_tool_dependencies:
        data[ 'install_tool_dependencies' ] = options.install_tool_dependencies
    submit( options.api, '%s%s' % ( options.local_url.rstrip( '/' ), '/api/tool_shed_repositories/new/install_repository_revision' ), data )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Installation of tool shed repositories via the Galaxy API.' )
    parser.add_argument( "-u", "--url", dest="tool_shed_url", required=True, help="Tool Shed URL" )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )
    parser.add_argument( "-l", "--local", dest="local_url", required=True, help="URL of the galaxy instance." )
    parser.add_argument( "-n", "--name", required=True, help="Repository name." )
    parser.add_argument( "-o", "--owner", required=True, help="Repository owner." )
    parser.add_argument( "-r", "--revision", dest="changeset_revision", help="Repository revision." )
    parser.add_argument( "--panel-section-id", dest="tool_panel_section_id", help="Tool panel section id if you want to add your repository to an existing tool section." )
    parser.add_argument( "--panel-section-name", dest="new_tool_panel_section_label", help="New tool panel section label. If specified a new tool section will be created." )
    parser.add_argument( "--repository-deps", dest="install_repository_dependencies", action="store_true", default=False, help="Install repository dependencies. [False]")
    parser.add_argument( "--tool-deps", dest="install_tool_dependencies", action="store_true", default=False, help="Install tool dependencies. [False]" )
    options = parser.parse_args()
    main( options )
