#!/usr/bin/env python
"""
Install a specified repository revision from a specified tool shed into Galaxy.  This example demonstrates installation of a repository that contains
valid tools, loading them into an existing section of the Galaxy tool panel.  The repository has no tool dependencies or repository dependencies, so only
a single repository will be installed.

This example requires a tool panel config file (e.g., tool_conf.xml, shed_tool_conf.xml, etc) to contain a tool panel section like the following:

<section id="from_test_tool_shed" name="From Test Tool Shed" version="">
</section>

usage: ./install_repository_tools_into_existing_tool_panel_section <api_key <galaxy base url> tool_shed_url name owner changeset_revision tool_panel_section_id

Here is a working example of how to use this script to install a repository from the test tool shed.
./install_repository_tools_into_existing_tool_panel_section.py <api key> <galaxy base url>/api/tool_shed_repositories/new/install_repository_revision http://testtoolshed.g2.bx.psu.edu gregs_filter greg f28d5018f9cb from_test_tool_shed
"""

import os
import sys
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import submit

try:
    assert sys.argv[ 7 ]
except IndexError:
    print 'usage: %s key url tool_shed_url name owner changeset_revision tool_panel_section_id' % os.path.basename( sys.argv[ 0 ] )
    sys.exit( 1 )

try:
    data = {}
    data[ 'tool_shed_url' ] = sys.argv[ 3 ]
    data[ 'name' ] = sys.argv[ 4 ]
    data[ 'owner' ] = sys.argv[ 5 ]
    data[ 'changeset_revision' ] = sys.argv[ 6 ]
    data[ 'tool_panel_section_id' ] = sys.argv[ 7 ]
except IndexError:
    print 'usage: %s key url tool_shed_url name owner changeset_revision tool_panel_section_id' % os.path.basename( sys.argv[ 0 ] )
    sys.exit( 1 )

submit( sys.argv[ 1 ], sys.argv[ 2 ], data )
