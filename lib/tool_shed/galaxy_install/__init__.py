"""
Classes encapsulating the management of repositories installed from Galaxy tool sheds.
"""
import os, logging
import tool_shed.util.shed_util_common
import tool_shed.util.datatype_util
from galaxy.model.orm import and_
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )

class InstalledRepositoryManager( object ):
    def __init__( self, app ):
        self.app = app
        self.model = self.app.model
        self.sa_session = self.model.context.current
        self.tool_configs = self.app.config.tool_configs
        if self.app.config.migrated_tools_config not in self.tool_configs:
            self.tool_configs.append( self.app.config.migrated_tools_config )
        self.installed_repository_dicts = []
    def get_repository_install_dir( self, tool_shed_repository ):
        for tool_config in self.tool_configs:
            tree, error_message = xml_util.parse_xml( tool_config )
            if tree is None:
                return None
            root = tree.getroot()
            tool_path = root.get( 'tool_path', None )
            if tool_path:
                ts = tool_shed.util.shed_util_common.clean_tool_shed_url( tool_shed_repository.tool_shed )
                relative_path = os.path.join( tool_path,
                                              ts,
                                              'repos',
                                              tool_shed_repository.owner,
                                              tool_shed_repository.name,
                                              tool_shed_repository.installed_changeset_revision )
                if os.path.exists( relative_path ):
                    return relative_path
        return None
    def load_proprietary_datatypes( self ):
        for tool_shed_repository in self.sa_session.query( self.model.ToolShedRepository ) \
                                                   .filter( and_( self.model.ToolShedRepository.table.c.includes_datatypes==True,
                                                                  self.model.ToolShedRepository.table.c.deleted==False ) ) \
                                                   .order_by( self.model.ToolShedRepository.table.c.id ):
            relative_install_dir = self.get_repository_install_dir( tool_shed_repository )
            if relative_install_dir:
                installed_repository_dict = tool_shed.util.datatype_util.load_installed_datatypes( self.app, tool_shed_repository, relative_install_dir )
                if installed_repository_dict:
                    self.installed_repository_dicts.append( installed_repository_dict )
    def load_proprietary_converters_and_display_applications( self, deactivate=False ):
        for installed_repository_dict in self.installed_repository_dicts:
            if installed_repository_dict[ 'converter_path' ]:
                tool_shed.util.datatype_util.load_installed_datatype_converters( self.app, installed_repository_dict, deactivate=deactivate )
            if installed_repository_dict[ 'display_path' ]:
                tool_shed.util.datatype_util.load_installed_display_applications( self.app, installed_repository_dict, deactivate=deactivate )
           