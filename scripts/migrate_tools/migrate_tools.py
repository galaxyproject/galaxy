"""
This script will start up its own web application which includes a ToolMigrationManager (~/lib/tool_shed/galaxy_install/tool_migration_manager.py).
For each tool discovered missing, the tool shed repository that contains it will be installed on disk and a new entry will be
created for it in the migrated_tools_conf.xml file.  These entries will be made so that the tool panel will be displayed the same
as it was before the tools were eliminated from the Galaxy distribution.  The ToolMigrationManager will properly handle entries in
migrated_tools_conf.xml for tools outside tool panel sections as well as tools inside tool panel sections, depending upon the
layout of the local tool_conf.xml file.  Entries will not be created in migrated_tools_conf.xml for tools included in the tool
shed repository but not defined in tool_conf.xml.
"""
from __future__ import print_function

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

from tool_shed.galaxy_install.migrate.common import MigrateToolsApplication

app = MigrateToolsApplication(sys.argv[1])
non_shed_tool_confs = app.tool_migration_manager.proprietary_tool_confs
if len(non_shed_tool_confs) == 1:
    plural = ''
    file_names = non_shed_tool_confs[0]
else:
    plural = 's'
    file_names = ', '.join(non_shed_tool_confs)
msg = "\nThe installation process is finished.  All tools associated with this migration that were defined in your file%s named\n" % plural
msg += "%s, have been removed.  You may now start your Galaxy server.\n" % file_names
print(msg)
app.shutdown()
sys.exit(0)
