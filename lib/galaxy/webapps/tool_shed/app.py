import config
import sys
from galaxy import tools
import galaxy.tools.data
import galaxy.quota
import galaxy.datatypes.registry
import galaxy.webapps.tool_shed.model
from galaxy.openid.providers import OpenIDProviders
from galaxy.util.dbkeys import GenomeBuilds
from galaxy.web import security
from galaxy.tags.tag_handler import CommunityTagHandler
from tool_shed.grids.repository_grid_filter_manager import RepositoryGridFilterManager
import tool_shed.repository_registry
import tool_shed.repository_types.registry


class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""

    def __init__( self, **kwd ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        self.name = "tool_shed"
        # Read the tool_shed.ini configuration file and check for errors.
        self.config = config.Configuration( **kwd )
        self.config.check()
        config.configure_logging( self.config )
        # Initialize the  Galaxy datatypes registry.
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        self.datatypes_registry.load_datatypes( self.config.root, self.config.datatypes_config )
        # Initialize the Tool Shed repository_types registry.
        self.repository_types_registry = tool_shed.repository_types.registry.Registry()
        # Initialize the RepositoryGridFilterManager.
        self.repository_grid_filter_manager = RepositoryGridFilterManager()
        # Determine the Tool Shed database connection string.
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        # Initialize the Tool Shed database and check for appropriate schema version.
        from galaxy.webapps.tool_shed.model.migrate.check import create_or_verify_database
        create_or_verify_database( db_url, self.config.database_engine_options )
        # Set up the Tool Shed database engine and ORM.
        from galaxy.webapps.tool_shed.model import mapping
        self.model = mapping.init( self.config.file_path,
                                   db_url,
                                   self.config.database_engine_options )
        # Initialize the Tool SHed security helper.
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        # initialize the Tool Shed tag handler.
        self.tag_handler = CommunityTagHandler()
        # Initialize the Tool Shed tool data tables.  Never pass a configuration file here
        # because the Tool Shed should always have an empty dictionary!
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager( self.config.tool_data_path )
        self.genome_builds = GenomeBuilds( self )
        # Citation manager needed to load tools.
        from galaxy.managers.citations import CitationsManager
        self.citations_manager = CitationsManager( self )
        # The Tool Shed makes no use of a Galaxy toolbox, but this attribute is still required.
        self.toolbox = tools.ToolBox( [], self.config.tool_path, self )
        # Initialize the Tool Shed security agent.
        self.security_agent = self.model.security_agent
        # The Tool Shed makes no use of a quota, but this attribute is still required.
        self.quota_agent = galaxy.quota.NoQuotaAgent( self.model )
        # TODO: Add OpenID support
        self.openid_providers = OpenIDProviders()
        # Initialize the baseline Tool Shed statistics component.
        self.shed_counter = self.model.shed_counter
        # Let the Tool Shed's HgwebConfigManager know where the hgweb.config file is located.
        self.hgweb_config_manager = self.model.hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = self.config.hgweb_config_dir
        # Initialize the repository registry.
        self.repository_registry = tool_shed.repository_registry.Registry( self )
        print >> sys.stderr, "Tool shed hgweb.config file is: ", self.hgweb_config_manager.hgweb_config

    def shutdown( self ):
        pass
