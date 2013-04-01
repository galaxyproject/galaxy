import sys, os, ConfigParser
import galaxy.config
import galaxy.datatypes.registry
from galaxy import tools
from galaxy.tools.data import *
import galaxy.model.mapping
import galaxy.tools.search
from galaxy.objectstore import build_object_store_from_config
import tool_shed.tool_shed_registry
from tool_shed.galaxy_install import install_manager

class MigrateToolsApplication( object ):
    """Encapsulates the state of a basic Galaxy Universe application in order to initiate the Install Manager"""
    def __init__( self, tools_migration_config ):
        install_dependencies = 'install_dependencies' in sys.argv
        galaxy_config_file = 'universe_wsgi.ini'
        self.name = 'galaxy'
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
        if not self.config.database_connection:
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
        # Initialize tool data tables using the config defined by self.config.tool_data_table_config_path.
        self.tool_data_tables = ToolDataTableManager( tool_data_path=self.config.tool_data_path,
                                                      config_filename=self.config.tool_data_table_config_path )
        # Load additional entries defined by self.config.shed_tool_data_table_config into tool data tables.
        self.tool_data_tables.load_from_config_file( config_filename=self.config.shed_tool_data_table_config,
                                                     tool_data_path=self.tool_data_tables.tool_data_path,
                                                     from_shed_config=True )
        # Initialize the tools, making sure the list of tool configs includes the reserved migrated_tools_conf.xml file.
        tool_configs = self.config.tool_configs
        if self.config.migrated_tools_config not in tool_configs:
            tool_configs.append( self.config.migrated_tools_config )
        self.toolbox = tools.ToolBox( tool_configs, self.config.tool_path, self )
        # Search support for tools
        self.toolbox_search = galaxy.tools.search.ToolBoxSearch( self.toolbox )
        # Set up the tool sheds registry.
        if os.path.isfile( self.config.tool_sheds_config ):
            self.tool_shed_registry = tool_shed.tool_shed_registry.Registry( self.config.root, self.config.tool_sheds_config )
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
                                                               migrated_tools_config=self.config.migrated_tools_config,
                                                               install_dependencies=install_dependencies )
    @property
    def sa_session( self ):
        return self.model.context.current
    def shutdown( self ):
        self.object_store.shutdown()
