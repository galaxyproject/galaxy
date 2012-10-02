import sys, os, ConfigParser, urllib2
import galaxy.config
import galaxy.datatypes.registry
from galaxy import util, tools
import galaxy.model.mapping
import galaxy.tools.search
from galaxy.objectstore import build_object_store_from_config
import galaxy.tool_shed.tool_shed_registry
from galaxy.tool_shed import install_manager
from galaxy.tool_shed.encoding_util import *
from galaxy.util.odict import odict

REPOSITORY_OWNER = 'devteam'

def check_for_missing_tools( app, tool_panel_configs, latest_tool_migration_script_number ):
    # Get the 000x_tools.xml file associated with the current migrate_tools version number.
    tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
    # Parse the XML and load the file attributes for later checking against the proprietary tool_panel_config.
    migrated_tool_configs_dict = odict()
    tree = util.parse_xml( tools_xml_file_path )
    root = tree.getroot()
    tool_shed = root.get( 'name' )
    tool_shed_url = get_tool_shed_url_from_tools_xml_file_path( app, tool_shed )
    # The default behavior is that the tool shed is down.
    tool_shed_accessible = False
    if tool_shed_url:
        for elem in root:
            if elem.tag == 'repository':
                tool_dependencies = []
                tool_dependencies_dict = {}
                repository_name = elem.get( 'name' )
                changeset_revision = elem.get( 'changeset_revision' )
                url = '%s/repository/get_tool_dependencies?name=%s&owner=%s&changeset_revision=%s&from_install_manager=True' % \
                ( tool_shed_url, repository_name, REPOSITORY_OWNER, changeset_revision )
                try:
                    response = urllib2.urlopen( url )
                    text = response.read()
                    response.close()
                    tool_shed_accessible = True
                except Exception, e:
                    # Tool shed may be unavailable - we have to set tool_shed_accessible since we're looping.
                    tool_shed_accessible = False
                    print "The URL\n%s\nraised the exception:\n%s\n" % ( url, str( e ) )
                if tool_shed_accessible:
                    if text:
                        tool_dependencies_dict = tool_shed_decode( text )
                        for dependency_key, requirements_dict in tool_dependencies_dict.items():
                            tool_dependency_name = requirements_dict[ 'name' ]
                            tool_dependency_version = requirements_dict[ 'version' ]
                            tool_dependency_type = requirements_dict[ 'type' ]
                            tool_dependency_readme = requirements_dict.get( 'readme', '' )
                            tool_dependencies.append( ( tool_dependency_name, tool_dependency_version, tool_dependency_type, tool_dependency_readme ) )
                    for tool_elem in elem.findall( 'tool' ):
                        migrated_tool_configs_dict[ tool_elem.get( 'file' ) ] = tool_dependencies
        if tool_shed_accessible:
            # Parse the proprietary tool_panel_configs (the default is tool_conf.xml) and generate the list of missing tool config file names.
            missing_tool_configs_dict = odict()
            for tool_panel_config in tool_panel_configs:
                tree = util.parse_xml( tool_panel_config )
                root = tree.getroot()
                for elem in root:
                    if elem.tag == 'tool':
                        missing_tool_configs_dict = check_tool_tag_set( elem, migrated_tool_configs_dict, missing_tool_configs_dict )
                    elif elem.tag == 'section':
                        for section_elem in elem:
                            if section_elem.tag == 'tool':
                                missing_tool_configs_dict = check_tool_tag_set( section_elem, migrated_tool_configs_dict, missing_tool_configs_dict )
    else:
        exception_msg = '\n\nThe entry for the main Galaxy tool shed at %s is missing from the %s file.  ' % ( tool_shed, app.config.tool_sheds_config )
        exception_msg += 'The entry for this tool shed must always be available in this file, so re-add it before attempting to start your Galaxy server.\n'
        raise Exception( exception_msg )  
    return tool_shed_accessible, missing_tool_configs_dict
def check_tool_tag_set( elem, migrated_tool_configs_dict, missing_tool_configs_dict ):
    file_path = elem.get( 'file', None )
    if file_path:
        path, name = os.path.split( file_path )
        if name in migrated_tool_configs_dict:
            tool_dependencies = migrated_tool_configs_dict[ name ]
            missing_tool_configs_dict[ name ] = tool_dependencies
    return missing_tool_configs_dict
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
def get_tool_shed_url_from_tools_xml_file_path( app, tool_shed ):
    search_str = '://%s' % tool_shed
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( search_str ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    return None

class MigrateToolsApplication( object ):
    """Encapsulates the state of a basic Galaxy Universe application in order to initiate the Install Manager"""
    def __init__( self, tools_migration_config ):
        install_dependencies = 'install_dependencies' in sys.argv
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
        # Tool data tables
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager( self.config.tool_data_path, self.config.tool_data_table_config_path )
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
                                                               migrated_tools_config=self.config.migrated_tools_config,
                                                               install_dependencies=install_dependencies )
    @property
    def sa_session( self ):
        return self.model.context.current
    def shutdown( self ):
        self.object_store.shutdown()
