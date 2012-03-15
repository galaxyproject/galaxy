
"""
This script will start up its own web application which includes an InstallManager (~/lib/galaxy/tool_shed/install_manager.py).
For each tool discovered missing, the tool shed repository that contains it will be installed on disk and a new entry will be
created for it in the migrated_tools_conf.xml file.  These entries will be made so that the tool panel will be displayed the same
as it was before the tools were eliminated from the Galaxy distribution.  The InstallManager will properly handle entries in 
migrated_tools_conf.xml for tools outside tool panel sections as well as tools inside tool panel sections, depending upon the
layout of the local tool_conf.xml file.  Entries will not be created in migrated_tools_conf.xml for tools included in the tool
shed repository but not defined in tool_conf.xml.
"""
import sys, os

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
# Remove scripts/ from the path.
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
from galaxy.tool_shed.migrate.common import *

app = MigrateToolsApplication( sys.argv[ 1 ] )
non_shed_tool_confs = app.install_manager.proprietary_tool_confs
if len( non_shed_tool_confs ) == 1:
    plural = ''
    file_names = non_shed_tool_confs[ 0 ]
else:
    plural = 's'
    file_names = ', '.join( non_shed_tool_confs )
msg = "\nThe installation process is finished.  You should now remove entries for the installed tools from your file%s named\n" % plural
msg += "%s and start your Galaxy server.\n" % file_names
print msg 
app.shutdown()
sys.exit( 0 )
