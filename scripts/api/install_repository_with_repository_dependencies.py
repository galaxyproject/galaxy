#!/usr/bin/env python
"""
Install a specified repository revision from a specified tool shed into Galaxy.  This example demonstrates installation of a repository that has
repository dependencies, so multiple repositories will ultimately be installed.  Since no Galaxy tool panel section information is used, all tools
contained in the installed repositories will be loaded into the Galaxy tool panel outside of any sections.

usage: ./install_repository_tools_into_existing_tool_panel_section <api_key <galaxy base url> tool_shed_url name owner changeset_revision True

Here is a working example of how to use this script to install a repository from the test tool shed.
./install_repository_tools_into_existing_tool_panel_section.py <api key> <galaxy base url>/api/tool_shed_repositories/new/install_repository_revision http://testtoolshed.g2.bx.psu.edu emboss_5 devteam 8ddad0c9a75a True
"""

import os
import sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

try:
    assert sys.argv[ 7 ]
except IndexError:
    print 'usage: %s key url tool_shed_url name owner changeset_revision install_repository_dependencies' % os.path.basename( sys.argv[ 0 ] )
    sys.exit( 1 )

try:
    data = {}
    data[ 'tool_shed_url' ] = sys.argv[ 3 ]
    data[ 'name' ] = sys.argv[ 4 ]
    data[ 'owner' ] = sys.argv[ 5 ]
    data[ 'changeset_revision' ] = sys.argv[ 6 ]
    data[ 'install_repository_dependencies' ] = sys.argv[ 7 ]
except IndexError:
    print 'usage: %s key url tool_shed_url name owner changeset_revision install_repository_dependencies' % os.path.basename( sys.argv[ 0 ] )
    sys.exit( 1 )

submit( sys.argv[ 1 ], sys.argv[ 2 ], data )