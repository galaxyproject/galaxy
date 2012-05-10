import sys, config
import galaxy.tools.data
import galaxy.quota
import galaxy.datatypes.registry
import galaxy.webapps.community.model
from galaxy.openid.providers import OpenIDProviders
from galaxy.web import security
from galaxy.tags.tag_handler import CommunityTagHandler

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        # Set up datatypes registry
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        # TODO: Handle datatypes included in repositories - the following will only load datatypes_conf.xml.
        self.datatypes_registry.load_datatypes( self.config.root, self.config.datatypes_config )
        # Determine the database url
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite://%s?isolation_level=IMMEDIATE" % self.config.database
        # Initialize database / check for appropriate schema version
        from galaxy.webapps.community.model.migrate.check import create_or_verify_database
        create_or_verify_database( db_url, self.config.database_engine_options )
        # Setup the database engine and ORM
        from galaxy.webapps.community.model import mapping
        self.model = mapping.init( self.config.file_path,
                                   db_url,
                                   self.config.database_engine_options )
        # Security helper
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        # Tag handler
        self.tag_handler = CommunityTagHandler()
        # Tool data tables
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager( self.config.tool_data_table_config_path )
        # The tool shed has no toolbox, but this attribute is still required.
        self.toolbox = None
        # Load security policy
        self.security_agent = self.model.security_agent
        self.quota_agent = galaxy.quota.NoQuotaAgent( self.model )
        # TODO: Add OpenID support
        self.openid_providers = OpenIDProviders()
        self.shed_counter = self.model.shed_counter
    def shutdown( self ):
        pass
