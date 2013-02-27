import sys, config
from galaxy import tools
import galaxy.tools.data
import galaxy.quota
import galaxy.datatypes.registry
import galaxy.webapps.tool_shed.model
from galaxy.openid.providers import OpenIDProviders
from galaxy.web import security
from galaxy.tags.tag_handler import CommunityTagHandler

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        self.name = "tool_shed"
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        # Set up datatypes registry
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        self.datatypes_registry.load_datatypes( self.config.root, self.config.datatypes_config )
        # Determine the database url
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        # Initialize database / check for appropriate schema version
        from galaxy.webapps.tool_shed.model.migrate.check import create_or_verify_database
        create_or_verify_database( db_url, self.config.database_engine_options )
        # Setup the database engine and ORM
        from galaxy.webapps.tool_shed.model import mapping
        self.model = mapping.init( self.config.file_path,
                                   db_url,
                                   self.config.database_engine_options )
        # Security helper
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        # Tag handler
        self.tag_handler = CommunityTagHandler()
        # Tool data tables - never pass a config file here because the tool shed should always have an empty dictionary!
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager( self.config.tool_data_path )
        # The tool shed has no toolbox, but this attribute is still required.
        self.toolbox = tools.ToolBox( [], self.config.tool_path, self )
        # Load security policy
        self.security_agent = self.model.security_agent
        self.quota_agent = galaxy.quota.NoQuotaAgent( self.model )
        # TODO: Add OpenID support
        self.openid_providers = OpenIDProviders()
        self.shed_counter = self.model.shed_counter
        # Let the HgwebConfigManager know where the hgweb.config file is located.
        self.hgweb_config_manager = self.model.hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = self.config.hgweb_config_dir
        print >> sys.stderr, "Tool shed hgweb.config file is: ", self.hgweb_config_manager.hgweb_config
    def shutdown( self ):
        pass
