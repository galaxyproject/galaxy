import logging
import sys
import time
from typing import Optional

from sqlalchemy.orm.scoping import scoped_session

import galaxy.datatypes.registry
import galaxy.tools.data
import tool_shed.repository_registry
import tool_shed.repository_types.registry
import tool_shed.webapp.model
from galaxy import auth
from galaxy.app import (
    HaltableContainer,
    SentryClientMixin,
)
from galaxy.config import configure_logging
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.citations import CitationsManager
from galaxy.managers.dbkeys import GenomeBuilds
from galaxy.managers.users import UserManager
from galaxy.model.base import SharedModelMapping
from galaxy.model.tags import CommunityTagHandler
from galaxy.quota import (
    NoQuotaAgent,
    QuotaAgent,
)
from galaxy.security import idencoding
from galaxy.structured_app import BasicSharedApp
from galaxy.web_stack import application_stack_instance
from tool_shed.grids.repository_grid_filter_manager import RepositoryGridFilterManager
from tool_shed.managers.model_cache import ModelCache
from tool_shed.structured_app import ToolShedApp
from tool_shed.util.hgweb_config import hgweb_config_manager
from tool_shed.webapp.model.migrations import verify_database
from . import config

log = logging.getLogger(__name__)


class UniverseApplication(ToolShedApp, SentryClientMixin, HaltableContainer):
    """Encapsulates the state of a Universe application"""

    def __init__(self, **kwd) -> None:
        super().__init__()
        self[BasicSharedApp] = self
        self[ToolShedApp] = self
        log.debug("python path is: %s", ", ".join(sys.path))
        self.name = "tool_shed"
        # will be overwritten when building WSGI app
        self.is_webapp = False
        # Read the tool_shed.ini configuration file and check for errors.
        self.config = config.Configuration(**kwd)
        self.config.check()
        configure_logging(self.config)
        self.application_stack = application_stack_instance()
        # Initialize the  Galaxy datatypes registry.
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        self.datatypes_registry.load_datatypes(self.config.root, self.config.datatypes_config)
        # Initialize the Tool Shed repository_types registry.
        self.repository_types_registry = tool_shed.repository_types.registry.Registry()
        # Initialize the RepositoryGridFilterManager.
        self.repository_grid_filter_manager = RepositoryGridFilterManager()
        # Determine the Tool Shed database connection string.
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = f"sqlite:///{self.config.database}?isolation_level=IMMEDIATE"

        # Initialize the Tool Shed database and check for appropriate schema version.
        verify_database(db_url, self.config.database_engine_options)

        # Set up the Tool Shed database engine and ORM.
        from tool_shed.webapp.model import mapping

        model: mapping.ToolShedModelMapping = mapping.init(db_url, self.config.database_engine_options)
        self.model = model
        self.security = idencoding.IdEncodingHelper(id_secret=self.config.id_secret)
        self._register_singleton(idencoding.IdEncodingHelper, self.security)
        self._register_singleton(SharedModelMapping, model)
        self._register_singleton(mapping.ToolShedModelMapping, model)
        self._register_singleton(scoped_session, self.model.context)
        self.model_cache = ModelCache(self.config.model_cache_dir)
        self.user_manager = self._register_singleton(UserManager, UserManager(self, app_type="tool_shed"))
        self.api_keys_manager = self._register_singleton(ApiKeyManager)
        # initialize the Tool Shed tag handler.
        self.tag_handler = CommunityTagHandler(self.model.context)
        # Initialize the Tool Shed tool data tables.  Never pass a configuration file here
        # because the Tool Shed should always have an empty dictionary!
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager(self.config.tool_data_path)
        self.genome_builds = GenomeBuilds(self)
        self.auth_manager = self._register_singleton(auth.AuthManager, auth.AuthManager(self.config))
        # Citation manager needed to load tools.
        self.citations_manager = self._register_singleton(CitationsManager, CitationsManager(self))
        self.use_tool_dependency_resolution = False
        # Initialize the Tool Shed security agent.
        self.security_agent = model.security_agent
        # The Tool Shed makes no use of a quota, but this attribute is still required.
        self.quota_agent = self._register_singleton(QuotaAgent, NoQuotaAgent())
        # Initialize the baseline Tool Shed statistics component.
        self.shed_counter = model.shed_counter
        # Let the Tool Shed's HgwebConfigManager know where the hgweb.config file is located.
        self.hgweb_config_manager = hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = self.config.hgweb_config_dir
        self.hgweb_config_manager.hgweb_repo_prefix = self.config.hgweb_repo_prefix
        # Initialize the repository registry.
        if config.SHED_API_VERSION != "v2":
            self.repository_registry = tool_shed.repository_registry.Registry(self)
        else:
            self.repository_registry = tool_shed.repository_registry.NullRepositoryRegistry(self)
        # Configure Sentry client if configured
        self.configure_sentry_client()
        #  used for cachebusting -- refactor this into a *SINGLE* UniverseApplication base.
        self.server_starttime = int(time.time())
        log.debug("Tool shed hgweb.config file is: %s", self.hgweb_config_manager.hgweb_config)


# Global instance of the universe app.
app: Optional[ToolShedApp] = None
