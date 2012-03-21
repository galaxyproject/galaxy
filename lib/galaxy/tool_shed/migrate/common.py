import sys, os, ConfigParser
import galaxy.config
import galaxy.datatypes.registry
from galaxy import util, tools
import galaxy.model.mapping
import galaxy.tools.search
from galaxy.objectstore import build_object_store_from_config
import galaxy.tool_shed.tool_shed_registry
from galaxy.tool_shed import install_manager
from galaxy.tool_shed.migrate.common import *

def check_for_missing_tools( tool_panel_configs, latest_tool_migration_script_number ):
    # Get the 000x_tools.xml file associated with the current migrate_tools version number.
    tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
    # Parse the XML and load the file attributes for later checking against the proprietary tool_panel_config.
    migrated_tool_configs = []
    tree = util.parse_xml( tools_xml_file_path )
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'repository':
            for tool_elem in elem.findall( 'tool' ):
                migrated_tool_configs.append( tool_elem.get( 'file' ) )
    # Parse the proprietary tool_panel_configs (the default is tool_conf.xml) and generate the list of missing tool config file names.
    missing_tool_configs = []
    for tool_panel_config in tool_panel_configs:
        tree = util.parse_xml( tool_panel_config )
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'tool':
                missing_tool_configs = check_tool_tag_set( elem, migrated_tool_configs, missing_tool_configs )
            elif elem.tag == 'section':
                for section_elem in elem:
                    if section_elem.tag == 'tool':
                        missing_tool_configs = check_tool_tag_set( section_elem, migrated_tool_configs, missing_tool_configs )
    return missing_tool_configs
def check_tool_tag_set( elem, migrated_tool_configs, missing_tool_configs ):
    file_path = elem.get( 'file', None )
    if file_path:
        path, name = os.path.split( file_path )
        if name in migrated_tool_configs:
            missing_tool_configs.append( name )
    return missing_tool_configs
def get_non_shed_tool_panel_configs( app ):
    # Get the non-shed related tool panel configs - there can be more than one, and the default is tool_conf.xml.
    config_filenames = []
    for config_filename in app.config.tool_configs:
        # Any config file that includes a tool_path attribute in the root tag set like the following is shed-related.
        # <toolbox tool_path="../shed_tools">
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        tool_path = root.get( 'tool_path', None )
        if tool_path is None:
            config_filenames.append( config_filename )
    return config_filenames
class MigrateToolsApplication( object ):
    """Encapsulates the state of a basic Galaxy Universe application in order to initiate the Install Manager"""
    def __init__( self, tools_migration_config ):
        galaxy_config_file = 'universe_wsgi.ini'
        if '-c' in sys.argv:
            pos = sys.argv.index( '-c' )
            sys.argv.pop( pos )
            galaxy_config_file = sys.argv.pop( pos )
        if not os.path.exists( galaxy_config_file ):
            print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % galaxy_config_file
            sys.exit( 1 )
        config_parser = ConfigParser.ConfigParser( { 'here':os.getcwd() } )
        config_parser.read( galaxy_config_file )
        galaxy_config_dict = {}
        for key, value in config_parser.items( "app:main" ):
            galaxy_config_dict[ key ] = value
        self.config = galaxy.config.Configuration( **galaxy_config_dict )
        if self.config.database_connection is None:
            self.config.database_connection = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        self.config.update_integrated_tool_panel = True
        self.object_store = build_object_store_from_config( self.config )
        # Setup the database engine and ORM
        self.model = galaxy.model.mapping.init( self.config.file_path,
                                                self.config.database_connection,
                                                engine_options={},
                                                create_tables=False,
                                                object_store=self.object_store )
        # Create an empty datatypes registry.
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        # Load the data types in the Galaxy distribution, which are defined in self.config.datatypes_config.
        self.datatypes_registry.load_datatypes( self.config.root, self.config.datatypes_config )
        # Initialize the tools, making sure the list of tool configs includes the reserved migrated_tools_conf.xml file.
        tool_configs = self.config.tool_configs
        if self.config.migrated_tools_config not in tool_configs:
            tool_configs.append( self.config.migrated_tools_config )
        self.toolbox = tools.ToolBox( tool_configs, self.config.tool_path, self )
        # Search support for tools
        self.toolbox_search = galaxy.tools.search.ToolBoxSearch( self.toolbox )
        # Set up the tool sheds registry.
        if os.path.isfile( self.config.tool_sheds_config ):
            self.tool_shed_registry = galaxy.tool_shed.tool_shed_registry.Registry( self.config.root, self.config.tool_sheds_config )
        else:
            self.tool_shed_registry = None
        # Get the latest tool migration script number to send to the Install manager.
        latest_migration_script_number = int( tools_migration_config.split( '_' )[ 0 ] )
        # The value of migrated_tools_config is migrated_tools_conf.xml, and is reserved for containing only those tools that have been
        # eliminated from the distribution and moved to the tool shed.  A side-effect of instantiating the InstallManager is the automatic
        # installation of all appropriate tool shed repositories.
        self.install_manager = install_manager.InstallManager( app=self,
                                                               latest_migration_script_number=latest_migration_script_number,
                                                               tool_shed_install_config=os.path.join( self.config.root,
                                                                                                      'scripts',
                                                                                                      'migrate_tools',
                                                                                                      tools_migration_config ),
                                                               migrated_tools_config=self.config.migrated_tools_config )
    @property
    def sa_session( self ):
        return self.model.context.current
    def shutdown( self ):
        self.object_store.shutdown()
