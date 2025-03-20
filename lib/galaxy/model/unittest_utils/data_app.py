"""Mock GalaxyApp exposing config + functionality required for galaxy-data package.

There is a more expansive MockApp in test/unit/unittest_utils - but it isn't packaged
and it has dependencies from across the app. This mock application and config is
more appropriate for testing galaxy-data functionality and will be included with
galaxy-data.
"""

import os
import shutil
import tempfile
from typing import Optional

from galaxy import (
    model,
    objectstore,
)
from galaxy.datatypes import registry
from galaxy.files import (
    ConfiguredFileSources,
    NullConfiguredFileSources,
)
from galaxy.model.mapping import (
    GalaxyModelMapping,
    init,
)
from galaxy.model.security import GalaxyRBACAgent
from galaxy.model.tags import GalaxyTagHandler
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util.bunch import Bunch

GALAXY_TEST_UNITTEST_SECRET = "6e46ed6483a833c100e68cc3f1d0dd76"
GALAXY_TEST_IN_MEMORY_DB_CONNECTION = "sqlite:///:memory:"


class GalaxyDataTestConfig(Bunch):
    """Minimal Galaxy mock config object that exposes and uses only what is needed for the galaxy-data package."""

    security: IdEncodingHelper
    database_connection: str
    root: str
    data_dir: str
    _remove_root: bool

    def __init__(self, root=None, **kwd):
        Bunch.__init__(self, **kwd)
        if not root:
            root = tempfile.mkdtemp()
            self._remove_root = True
        else:
            self._remove_root = False
        self.root = root
        self.data_dir = os.path.join(root, "database")

        self.security = IdEncodingHelper(id_secret=GALAXY_TEST_UNITTEST_SECRET)
        self.database_connection = kwd.get("database_connection", GALAXY_TEST_IN_MEMORY_DB_CONNECTION)

        # objectstore config values...
        self.object_store_config_file = ""
        self.object_store_config = None
        self.object_store = "disk"
        self.object_store_check_old_style = False
        self.object_store_cache_path = "/tmp/cache"
        self.object_store_cache_size = -1
        self.object_store_store_by = "uuid"

        self.umask = os.umask(0o77)
        self.gid = os.getgid()
        # objectstore config directories...
        self.jobs_directory = os.path.join(self.data_dir, "jobs_directory")
        self.new_file_path = os.path.join(self.data_dir, "tmp")
        self.file_path = os.path.join(self.data_dir, "files")
        self.server_name = "main"
        self.enable_quotas = False
        self.user_library_import_symlink_allowlist = []
        self.fetch_url_allowlist_ips = []
        self.library_import_dir = None
        self.user_library_import_dir = None
        self.ftp_upload_dir = None
        self.ftp_upload_purge = False

        self.file_source_temp_dir = None
        self.file_source_webdav_use_temp_files = False
        self.file_source_listings_expiry_time = 60

    def __del__(self):
        if self._remove_root:
            shutil.rmtree(self.root)


class GalaxyDataTestApp:
    """Minimal Galaxy mock app object that exposes and uses only what is needed for the galaxy-data package."""

    security: IdEncodingHelper
    model: GalaxyModelMapping
    security_agent: GalaxyRBACAgent
    file_sources: ConfiguredFileSources = NullConfiguredFileSources()

    def __init__(self, config: Optional[GalaxyDataTestConfig] = None, **kwd):
        config = config or GalaxyDataTestConfig(**kwd)
        self.config = config
        self.security = config.security
        self.object_store = objectstore.build_object_store_from_config(self.config)
        self.model = init("/tmp", self.config.database_connection, create_tables=True)
        model.setup_global_object_store_for_models(self.object_store)
        self.security_agent = self.model.security_agent
        self.tag_handler = GalaxyTagHandler(self.model.session)
        self.init_datatypes()

    def init_datatypes(self):
        datatypes_registry = registry.Registry()
        datatypes_registry.load_datatypes()
        model.set_datatypes_registry(datatypes_registry)
        datatypes_registry.set_external_metadata_tool = MockSetExternalTool()
        self.datatypes_registry = datatypes_registry


class MockSetExternalTool:
    def regenerate_imported_metadata_if_needed(self, *args, **kwds):
        pass
