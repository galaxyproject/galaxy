"""
Mock infrastructure for testing ModelManagers.
"""
import os
import shutil
import tempfile
from typing import Any

from galaxy import (
    di,
    quota,
)
from galaxy.auth import AuthManager
from galaxy.celery import set_thread_app
from galaxy.config import CommonConfigurationMixin
from galaxy.jobs.manager import NoopManager
from galaxy.managers.users import UserManager
from galaxy.model import tags
from galaxy.model.base import SharedModelMapping
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.unittest_utils import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.security import idencoding
from galaxy.structured_app import (
    BasicSharedApp,
    MinimalManagerApp,
    StructuredApp,
)
from galaxy.tool_util.deps.containers import NullContainerFinder
from galaxy.tools.data import ToolDataTableManager
from galaxy.util import StructuredExecutionTimer
from galaxy.util.bunch import Bunch
from galaxy.util.dbkeys import GenomeBuilds
from galaxy.web.short_term_storage import (
    ShortTermStorageAllocator,
    ShortTermStorageConfiguration,
    ShortTermStorageManager,
    ShortTermStorageMonitor,
)
from galaxy.web_stack import ApplicationStack


# =============================================================================
def buildMockEnviron(**kwargs):
    environ = {
        "CONTENT_LENGTH": "0",
        "CONTENT_TYPE": "",
        "HTTP_ACCEPT": "*/*",
        "HTTP_ACCEPT_ENCODING": "gzip, deflate",
        "HTTP_ACCEPT_LANGUAGE": "en-US,en;q=0.8,zh;q=0.5,ja;q=0.3",
        "HTTP_CACHE_CONTROL": "no-cache",
        "HTTP_CONNECTION": "keep-alive",
        "HTTP_DNT": "1",
        "HTTP_HOST": "localhost:8000",
        "HTTP_ORIGIN": "http://localhost:8000",
        "HTTP_PRAGMA": "no-cache",
        "HTTP_REFERER": "http://localhost:8000",
        "HTTP_USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:43.0) Gecko/20100101 Firefox/43.0",
        "PATH_INFO": "/",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": "GET",
        "SCRIPT_NAME": "",
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8080",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    environ.update(**kwargs)
    return environ


class MockApp(di.Container, GalaxyDataTestApp):
    config: "MockAppConfig"

    def __init__(self, config=None, **kwargs):
        super().__init__()
        config = config or MockAppConfig(**kwargs)
        GalaxyDataTestApp.__init__(self, config=config, **kwargs)
        self[BasicSharedApp] = self
        self[MinimalManagerApp] = self
        self[StructuredApp] = self
        self[idencoding.IdEncodingHelper] = self.security
        self.name = kwargs.get("name", "galaxy")
        self[SharedModelMapping] = self.model
        self[GalaxyModelMapping] = self.model
        sts_config = ShortTermStorageConfiguration(short_term_storage_directory=os.path.join(config.data_dir, "sts"))
        sts_manager = ShortTermStorageManager(sts_config)
        self[ShortTermStorageAllocator] = sts_manager
        self[ShortTermStorageMonitor] = sts_manager
        self[galaxy_scoped_session] = self.model.context
        self.visualizations_registry = MockVisualizationsRegistry()
        self.tag_handler = tags.GalaxyTagHandler(self.model.context)
        self[tags.GalaxyTagHandler] = self.tag_handler
        self.quota_agent = quota.DatabaseQuotaAgent(self.model)
        self.job_config = Bunch(dynamic_params=None, destinations={}, assign_handler=lambda *args, **kwargs: None)
        self.tool_data_tables = ToolDataTableManager(tool_data_path=self.config.tool_data_path)
        self.dataset_collections_service = None
        self.container_finder = NullContainerFinder()
        self._toolbox_lock = MockLock()
        self.tool_shed_registry = Bunch(tool_sheds={})
        self.genome_builds = GenomeBuilds(self)
        self.job_manager = NoopManager()
        self.application_stack = ApplicationStack()
        self.auth_manager = AuthManager(self.config)
        self.user_manager = UserManager(self)
        self.execution_timer_factory = Bunch(get_timer=StructuredExecutionTimer)
        self.interactivetool_manager = Bunch(create_interactivetool=lambda *args, **kwargs: None)
        self.is_job_handler = False
        self.biotools_metadata_source = None
        set_thread_app(self)

        def url_for(*args, **kwds):
            return "/mock/url"

        self.url_for = url_for

    def wait_for_toolbox_reload(self, toolbox):
        # TODO: If the tpm test case passes, does the operation really
        # need to wait.
        return True


class MockLock:
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass


class MockAppConfig(GalaxyDataTestConfig, CommonConfigurationMixin):
    class MockSchema(Bunch):
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.schema = self.MockSchema()
        self.use_remote_user = kwargs.get("use_remote_user", False)
        self.enable_celery_tasks = False
        self.tool_data_path = os.path.join(self.root, "tool-data")
        self.galaxy_data_manager_data_path = self.tool_data_path
        self.tool_dependency_dir = None
        self.metadata_strategy = "directory"

        self.user_activation_on = False
        self.new_user_dataset_access_role_default_private = False

        self.expose_dataset_path = True
        self.allow_user_dataset_purge = True
        self.allow_user_creation = True
        self.email_domain_allowlist_content = None
        self.email_domain_blocklist_content = None
        self.enable_old_display_applications = True
        self.redact_username_in_logs = False
        self.auth_config_file = "config/auth_conf.xml.sample"
        self.error_email_to = "admin@email.to"
        self.password_expiration_period = 0

        self.umask = 0o77
        self.flush_per_n_datasets = 0

        # Compliance related config
        self.redact_email_in_job_name = False

        # Follow two required by GenomeBuilds
        self.len_file_path = os.path.join("tool-data", "shared", "ucsc", "chrom")
        self.builds_file_path = os.path.join("tool-data", "shared", "ucsc", "builds.txt.sample")

        self.shed_tool_config_file = "config/shed_tool_conf.xml"
        self.shed_tool_config_file_set = False
        self.enable_beta_edam_toolbox = False
        self.preserve_python_environment = "always"
        self.enable_beta_gdpr = False

        self.version_major = "19.09"

        # set by MockDir
        self.enable_tool_document_cache = False
        self.tool_cache_data_dir = os.path.join(self.root, "tool_cache")
        self.delay_tool_initialization = True
        self.external_chown_script = None
        self.check_job_script_integrity = False
        self.check_job_script_integrity_count = 0
        self.check_job_script_integrity_sleep = 0

        self.default_panel_view = "default"
        self.panel_views_dir = ""
        self.panel_views = {}
        self.edam_panel_views = ""

        self.config_file = None

        self._admin_users = ""
        self.drmaa_external_runjob_script = None
        self.tool_secret = None
        self.track_jobs_in_database = False
        self.amqp_internal_connection = None
        self.tool_configs = []
        self.manage_dependency_relationships = False
        self.enable_tool_shed_check = False
        self.monitor_thread_join_timeout = 1
        self.integrated_tool_panel_config = None
        self.vault_config_file = kwargs.get("vault_config_file")
        self.max_discovered_files = 10000

    @property
    def config_dict(self):
        return self.dict()

    def __getattr__(self, name):
        # Handle the automatic [option]_set options: for tests, assume none are set
        if name == "is_set":
            return lambda x: False
        # Handle the automatic config file _set options
        if name.endswith("_file_set"):
            return False
        raise AttributeError(name)


class MockWebapp:
    def __init__(self, security: idencoding.IdEncodingHelper, **kwargs):
        self.name = kwargs.get("name", "galaxy")
        self.security = security


class MockTrans:
    def __init__(self, app=None, user=None, history=None, **kwargs):
        self.app = app or MockApp(**kwargs)
        self.model = self.app.model
        self.webapp = MockWebapp(self.app.security, **kwargs)
        self.sa_session = self.app.model.session
        self.workflow_building_mode = False
        self.error_message = None
        self.anonymous = False
        self.debug = True
        self.user_is_admin = True
        self.url_builder = None

        self.galaxy_session = None
        self.__user = user
        self.security = self.app.security
        self.history = history

        self.request: Any = Bunch(headers={}, body=None)
        self.response: Any = Bunch(headers={}, set_content_type=lambda i: None)

    def check_csrf_token(self, payload):
        pass

    def handle_user_login(self, user):
        pass

    def log_event(self, message):
        pass

    def get_user(self):
        if self.galaxy_session:
            return self.galaxy_session.user
        else:
            return self.__user

    def set_user(self, user):
        """Set the current user."""
        if self.galaxy_session:
            self.galaxy_session.user = user
            self.sa_session.add(self.galaxy_session)
            self.sa_session.flush()
        self.__user = user

    user = property(get_user, set_user)

    def get_history(self, **kwargs):
        return self.history

    def set_history(self, history):
        self.history = history

    def fill_template(self, filename, template_lookup=None, **kwargs):
        template = template_lookup.get_template(filename)
        kwargs.update(h=MockTemplateHelpers())
        return template.render(**kwargs)


class MockVisualizationsRegistry:
    BUILT_IN_VISUALIZATIONS = ["trackster"]

    def get_visualizations(self, trans, target):
        return []


class MockDir:
    def __init__(self, structure_dict, where=None):
        self.structure_dict = structure_dict
        self.create_root(structure_dict, where)

    def create_root(self, structure_dict, where=None):
        self.root_path = tempfile.mkdtemp(dir=where)
        self.create_structure(self.root_path, structure_dict)

    def create_structure(self, current_path, structure_dict):
        for k, v in structure_dict.items():
            # if value is string, create a file in the current path and write v as file contents
            if isinstance(v, str):
                self.create_file(os.path.join(current_path, k), v)
            # if it's a dict, create a dir here named k and recurse into it
            if isinstance(v, dict):
                subdir_path = os.path.join(current_path, k)
                os.mkdir(subdir_path)
                self.create_structure(subdir_path, v)

    def create_file(self, path, contents):
        with open(path, "w") as newfile:
            newfile.write(contents)

    def remove(self):
        shutil.rmtree(self.root_path)


class MockTemplateHelpers:
    def js(*js_files):
        pass

    def css(*css_files):
        pass
