"""Scripts for drivers of Galaxy functional tests."""

import http.client
import json
import logging
import os
import random
import shutil
import socket
import string
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from urllib.parse import urlparse

from galaxy.app import UniverseApplication as GalaxyUniverseApplication
from galaxy.config import LOGGING_CONFIG_DEFAULT
from galaxy.model import mapping
from galaxy.model.database_utils import (
    create_database,
    database_exists,
)
from galaxy.model.tool_shed_install import mapping as toolshed_mapping
from galaxy.tool_util.verify.interactor import (
    GalaxyInteractorApi,
    verify_tool,
)
from galaxy.util import (
    asbool,
    download_to_file,
    galaxy_directory,
)
from galaxy.util.properties import load_app_properties
from galaxy.webapps.galaxy import buildapp
from galaxy.webapps.galaxy.fast_app import initialize_fast_app as init_galaxy_fast_app
from galaxy_test.base.api_util import (
    get_admin_api_key,
    get_user_api_key,
)
from galaxy_test.base.env import (
    DEFAULT_WEB_HOST,
    target_url_parts,
)
from .test_logging import logging_config_file

galaxy_root = galaxy_directory()
DEFAULT_CONFIG_PREFIX = "GALAXY"
GALAXY_TEST_DIRECTORY = os.path.join(galaxy_root, "test")
GALAXY_TEST_FILE_DIR = "test-data,https://github.com/galaxyproject/galaxy-test-data.git"
TOOL_SHED_TEST_DATA = os.path.join(galaxy_root, "lib", "tool_shed", "test", "test_data")
TEST_WEBHOOKS_DIR = os.path.join(galaxy_root, "test", "functional", "webhooks")
FRAMEWORK_TOOLS_DIR = os.path.join(GALAXY_TEST_DIRECTORY, "functional", "tools")
FRAMEWORK_UPLOAD_TOOL_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "upload_tool_conf.xml")
FRAMEWORK_SAMPLE_TOOLS_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "sample_tool_conf.xml")
FRAMEWORK_DATATYPES_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "sample_datatypes_conf.xml")
MIGRATED_TOOL_PANEL_CONFIG = "config/migrated_tools_conf.xml"
INSTALLED_TOOL_PANEL_CONFIGS = [os.environ.get("GALAXY_TEST_SHED_TOOL_CONF", "config/shed_tool_conf.xml")]
DEFAULT_LOCALES = "en"

log = logging.getLogger("test_driver")


# Global variable to pass database contexts around - only needed for older
# Tool Shed twill tests that didn't utilize the API for such interactions.
install_context = None


def setup_tool_shed_tmp_dir():
    tool_shed_test_tmp_dir = os.environ.get("TOOL_SHED_TEST_TMP_DIR", None)
    if tool_shed_test_tmp_dir is None:
        tool_shed_test_tmp_dir = os.path.realpath(tempfile.mkdtemp())
    # Here's the directory where everything happens.  Temporary directories are created within this directory to contain
    # the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
    # the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
    os.environ["TOOL_SHED_TEST_TMP_DIR"] = tool_shed_test_tmp_dir
    return tool_shed_test_tmp_dir


def get_galaxy_test_tmp_dir():
    """Create test directory for use by Galaxy server being setup for testing."""
    galaxy_test_tmp_dir = os.environ.get("GALAXY_TEST_TMP_DIR", None)
    if galaxy_test_tmp_dir is None:
        galaxy_test_tmp_dir = tempfile.mkdtemp()
    return galaxy_test_tmp_dir


def build_logger():
    """Build a logger for test driver script."""
    return log


def ensure_test_file_dir_set():
    """Ensure GALAXY_TEST_FILE_DIR setup in environment for test data resolver.

    Return first directory for backward compat.
    """
    galaxy_test_file_dir = os.environ.get("GALAXY_TEST_FILE_DIR", GALAXY_TEST_FILE_DIR)
    os.environ["GALAXY_TEST_FILE_DIR"] = galaxy_test_file_dir
    first_test_file_dir = galaxy_test_file_dir.split(",")[0]
    return first_test_file_dir


def setup_galaxy_config(
    tmpdir,
    use_test_file_dir=False,
    default_install_db_merged=True,
    default_tool_data_table_config_path=None,
    default_shed_tool_data_table_config=None,
    default_job_config_file=None,
    enable_tool_shed_check=False,
    default_tool_conf=None,
    shed_tool_conf=None,
    datatypes_conf=None,
    update_integrated_tool_panel=False,
    prefer_template_database=False,
    log_format=None,
    conda_auto_init=False,
    conda_auto_install=False,
    use_shared_connection_for_amqp=False,
    allow_tool_conf_override: bool = True,
    allow_path_paste=False,
):
    """Setup environment and build config for test Galaxy instance."""
    # For certain docker operations this needs to be evaluated out - e.g. for cwltool.
    tmpdir = os.path.realpath(tmpdir)
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    template_cache_path = tempfile.mkdtemp(prefix="compiled_templates_", dir=tmpdir)
    new_file_path = tempfile.mkdtemp(prefix="new_files_path_", dir=tmpdir)
    job_working_directory = tempfile.mkdtemp(prefix="job_working_directory_", dir=tmpdir)

    user_library_import_dir: Optional[str]
    if use_test_file_dir:
        first_test_file_dir = ensure_test_file_dir_set()
        if not os.path.isabs(first_test_file_dir):
            first_test_file_dir = os.path.join(galaxy_root, first_test_file_dir)
        library_import_dir = first_test_file_dir
        import_dir = os.path.join(first_test_file_dir, "users")
        if os.path.exists(import_dir):
            user_library_import_dir = import_dir
        else:
            user_library_import_dir = None
    else:
        user_library_import_dir = None
        library_import_dir = None
    job_config_file = os.environ.get("GALAXY_TEST_JOB_CONFIG_FILE", default_job_config_file)
    tool_path = os.environ.get("GALAXY_TEST_TOOL_PATH", "tools")
    tool_data_table_config_path = _tool_data_table_config_path(default_tool_data_table_config_path)
    default_data_manager_config = None
    for data_manager_config in ["config/data_manager_conf.xml", "data_manager_conf.xml"]:
        if os.path.exists(data_manager_config):
            default_data_manager_config = data_manager_config
    data_manager_config_file = "test/functional/tools/sample_data_manager_conf.xml"
    if default_data_manager_config is not None:
        data_manager_config_file = f"{default_data_manager_config},{data_manager_config_file}"
    master_api_key = get_admin_api_key()
    cleanup_job = (
        "never"
        if ("GALAXY_TEST_NO_CLEANUP" in os.environ or "TOOL_SHED_TEST_NO_CLEANUP" in os.environ)
        else "onsuccess"
    )

    # Data Manager testing temp path
    # For storing Data Manager outputs and .loc files so that real ones don't get clobbered
    galaxy_data_manager_data_path = tempfile.mkdtemp(prefix="data_manager_tool-data", dir=tmpdir)

    if allow_tool_conf_override:
        tool_conf = os.environ.get("GALAXY_TEST_TOOL_CONF", default_tool_conf)
    else:
        tool_conf = default_tool_conf
    conda_auto_install = os.environ.get("GALAXY_TEST_CONDA_AUTO_INSTALL", conda_auto_install)
    conda_auto_init = os.environ.get("GALAXY_TEST_CONDA_AUTO_INIT", conda_auto_init)
    conda_prefix = os.environ.get("GALAXY_TEST_CONDA_PREFIX")
    if tool_conf is None:
        # As a fallback always at least allow upload.
        tool_conf = FRAMEWORK_UPLOAD_TOOL_CONF

    if shed_tool_conf is not None:
        tool_conf = f"{tool_conf},{shed_tool_conf}"

    # Resolve these paths w.r.t. galaxy root; otherwise galaxy's config system will resolve them w.r.t.
    # their parent directories, as per schema.
    data_manager_config_file = _resolve_relative_config_paths(data_manager_config_file)
    tool_config_file = _resolve_relative_config_paths(tool_conf)
    tool_data_table_config_path = _resolve_relative_config_paths(tool_data_table_config_path)

    config = dict(
        admin_users="test@bx.psu.edu",
        allow_library_path_paste=True,
        allow_path_paste=allow_path_paste,
        allow_user_creation=True,
        allow_user_deletion=True,
        api_allow_run_as="test@bx.psu.edu",
        auto_configure_logging=logging_config_file is None,
        chunk_upload_size=100,
        conda_prefix=conda_prefix,
        conda_auto_init=conda_auto_init,
        conda_auto_install=conda_auto_install,
        cleanup_job=cleanup_job,
        retry_metadata_internally=False,
        data_dir=tmpdir,
        data_manager_config_file=data_manager_config_file,
        enable_beta_tool_formats=True,
        expose_dataset_path=True,
        ftp_upload_purge=False,
        galaxy_data_manager_data_path=galaxy_data_manager_data_path,
        id_secret="changethisinproductiontoo",
        job_config_file=job_config_file,
        job_working_directory=job_working_directory,
        library_import_dir=library_import_dir,
        log_destination="stdout",
        new_file_path=new_file_path,
        override_tempdir=False,
        master_api_key=master_api_key,
        running_functional_tests=True,
        template_cache_path=template_cache_path,
        tool_config_file=tool_config_file,
        tool_data_table_config_path=tool_data_table_config_path,
        tool_path=tool_path,
        update_integrated_tool_panel=update_integrated_tool_panel,
        use_tasked_jobs=True,
        use_heartbeat=False,
        user_library_import_dir=user_library_import_dir,
        webhooks_dir=TEST_WEBHOOKS_DIR,
        logging=LOGGING_CONFIG_DEFAULT,
        monitor_thread_join_timeout=5,
        object_store_store_by="uuid",
        fetch_url_allowlist=["127.0.0.0/24"],
        job_handler_monitor_sleep=0.2,
        job_runner_monitor_sleep=0.2,
        workflow_monitor_sleep=0.2,
    )
    if default_shed_tool_data_table_config:
        config["shed_tool_data_table_config"] = default_shed_tool_data_table_config
    if not use_shared_connection_for_amqp:
        config["amqp_internal_connection"] = (
            f"sqlalchemy+sqlite:///{os.path.join(tmpdir, 'control.sqlite')}?isolation_level=IMMEDIATE"
        )

    config.update(database_conf(tmpdir, prefer_template_database=prefer_template_database))
    config.update(install_database_conf(tmpdir, default_merged=default_install_db_merged))
    if asbool(os.environ.get("GALAXY_TEST_USE_HIERARCHICAL_OBJECT_STORE")):
        object_store_config = os.path.join(tmpdir, "object_store_conf.yml")
        with open(object_store_config, "w") as f:
            contents = """
type: hierarchical
backends:
   - id: files1
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files1"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp1"
     - type: job_work
       path: "${temp_directory}/job_working_directory1"
   - id: files2
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files2"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp2"
     - type: job_work
       path: "${temp_directory}/job_working_directory2"
"""
            contents_template = string.Template(contents)
            expanded_contents = contents_template.safe_substitute(temp_directory=tmpdir)
            f.write(expanded_contents)
        config["object_store_config_file"] = object_store_config

    if datatypes_conf is not None:
        config["datatypes_config_file"] = datatypes_conf
    if enable_tool_shed_check:
        config["enable_tool_shed_check"] = enable_tool_shed_check
        config["hours_between_check"] = 0.001
    tool_dependency_dir = os.environ.get("GALAXY_TOOL_DEPENDENCY_DIR")
    if tool_dependency_dir:
        config["tool_dependency_dir"] = tool_dependency_dir
    # Used by shed's twill dependency stuff
    # TODO: read from Galaxy's config API.
    os.environ["GALAXY_TEST_TOOL_DEPENDENCY_DIR"] = tool_dependency_dir or os.path.join(tmpdir, "dependencies")
    return config


def _resolve_relative_config_paths(config_option):
    # If option is not None, split into paths, resolve each w.r.t. root, then rebuild as csv string.
    if config_option is not None:
        resolved = []
        for path in config_option.split(","):
            resolved.append(os.path.join(galaxy_root, path.strip()))
        return ",".join(resolved)


def _tool_data_table_config_path(default_tool_data_table_config_path=None):
    tool_data_table_config_path = os.environ.get(
        "GALAXY_TEST_TOOL_DATA_TABLE_CONF", default_tool_data_table_config_path
    )
    if tool_data_table_config_path is None:
        # ... otherwise find whatever Galaxy would use as the default and
        # the sample data for functional tests to that.
        default_tool_data_config = "lib/galaxy/config/sample/tool_data_table_conf.xml.sample"
        for tool_data_config in ["config/tool_data_table_conf.xml", "tool_data_table_conf.xml"]:
            if os.path.exists(tool_data_config):
                default_tool_data_config = tool_data_config
        test_tool_data_config = "test/functional/tool-data/sample_tool_data_tables.xml"
        tool_data_table_config_path = f"{default_tool_data_config},{test_tool_data_config}"
    return tool_data_table_config_path


def copy_database_template(source, db_path):
    """Copy a 'clean' sqlite template database.

    From file or URL to specified path for sqlite database.
    """
    db_path_dir = os.path.dirname(db_path)
    if not os.path.exists(db_path_dir):
        os.makedirs(db_path_dir)
    if os.path.exists(source):
        shutil.copy(source, db_path)
        assert os.path.exists(db_path)
    elif source.lower().startswith(("http://", "https://", "ftp://")):
        try:
            download_to_file(source, db_path)
        except Exception as e:
            # We log the exception but don't fail startup, since we can
            # do all migration steps instead of downloading a template.
            log.exception(e)
    else:
        raise Exception(f"Failed to copy database template from source {source}")


def init_database(database_connection):
    # We pass by migrations and instantiate the current table
    create_database(database_connection)
    mapping.init("/tmp", database_connection, create_tables=True, map_install_models=True)
    toolshed_mapping.init(database_connection, create_tables=True)


def database_conf(db_path, prefix="GALAXY", prefer_template_database=False):
    """Find (and populate if needed) Galaxy database connection."""
    database_auto_migrate = False
    check_migrate_databases = True
    dburi_var = f"{prefix}_TEST_DBURI"
    template_name = None
    if dburi_var in os.environ:
        database_connection = os.environ[dburi_var]
        # only template if postgres - not mysql or sqlite
        do_template = prefer_template_database and database_connection.startswith("p")
        if do_template:
            database_template_parsed = urlparse(database_connection)
            template_name = database_template_parsed.path[1:]  # drop / from /galaxy
            actual_db = f"gxtest{''.join(random.choice(string.ascii_uppercase) for _ in range(10))}"
            actual_database_parsed = database_template_parsed._replace(path=f"/{actual_db}")
            database_connection = actual_database_parsed.geturl()
            if not database_exists(database_connection):
                init_database(database_connection)
                check_migrate_databases = False
    else:
        default_db_filename = f"{prefix.lower()}.sqlite"
        template_var = f"{prefix}_TEST_DB_TEMPLATE"
        db_path = os.path.join(db_path, default_db_filename)
        if template_var in os.environ:
            # Middle ground between recreating a completely new
            # database and pointing at existing database with
            # GALAXY_TEST_DBURI. The former requires a lot of setup
            # time, the latter results in test failures in certain
            # cases (namely tool shed tests expecting clean database).
            copy_database_template(os.environ[template_var], db_path)
            database_auto_migrate = True
        database_connection = f"sqlite:///{db_path}"
    config = {
        "check_migrate_databases": check_migrate_databases,
        "database_connection": database_connection,
        "database_auto_migrate": database_auto_migrate,
    }
    if not database_connection.startswith("sqlite://"):
        config["database_engine_option_max_overflow"] = "20"
        config["database_engine_option_pool_size"] = "10"
    if template_name:
        config["database_template"] = template_name
    return config


def install_database_conf(db_path, default_merged=False):
    install_galaxy_database_connection: Optional[str]
    if "GALAXY_TEST_INSTALL_DBURI" in os.environ:
        install_galaxy_database_connection = os.environ["GALAXY_TEST_INSTALL_DBURI"]
    elif asbool(os.environ.get("GALAXY_TEST_INSTALL_DB_MERGED", default_merged)):
        install_galaxy_database_connection = None
    else:
        install_galaxy_db_path = os.path.join(db_path, "install.sqlite")
        install_galaxy_database_connection = f"sqlite:///{install_galaxy_db_path}"
    conf = {}
    if install_galaxy_database_connection is not None:
        conf["install_database_connection"] = install_galaxy_database_connection
    return conf


def database_files_path(test_tmpdir, prefix="GALAXY"):
    """Create a mock database/ directory like in GALAXY_ROOT.

    Use prefix to default this if TOOL_SHED_TEST_DBPATH or
    GALAXY_TEST_DBPATH is set in the environment.
    """
    environ_var = f"{prefix}_TEST_DBPATH"
    if environ_var in os.environ:
        db_path = os.environ[environ_var]
    else:
        tempdir = tempfile.mkdtemp(dir=test_tmpdir)
        db_path = os.path.join(tempdir, "database")
    return db_path


def _get_static_settings():
    """Configuration required for Galaxy static middleware.

    Returns dictionary of the settings necessary for a galaxy App
    to be wrapped in the static middleware.

    This mainly consists of the filesystem locations of url-mapped
    static resources.
    """
    static_dir = os.path.join(galaxy_root, "static")

    # TODO: these should be copied from config/galaxy.ini
    return dict(
        static_enabled=True,
        static_cache_time=360,
        static_dir=static_dir,
        static_images_dir=os.path.join(static_dir, "images", ""),
        static_favicon_dir=os.path.join(static_dir, "favicon.ico"),
        static_scripts_dir=os.path.join(static_dir, "scripts", ""),
        static_style_dir=os.path.join(static_dir, "style"),
        static_robots_txt=os.path.join(static_dir, "robots.txt"),
    )


def get_webapp_global_conf():
    """Get the global_conf dictionary sent to ``app_factory``."""
    # (was originally sent 'dict()') - nothing here for now except static settings
    global_conf = {}
    global_conf.update(_get_static_settings())
    return global_conf


def wait_for_http_server(host, port, prefix=None, sleep_amount=0.1, sleep_tries=150):
    """Wait for an HTTP server to boot up."""
    # Test if the server is up
    prefix = prefix or "/"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    for _ in range(sleep_tries):
        # directly test the app, not the proxy
        if port and isinstance(port, str):
            port = int(port)
        conn = http.client.HTTPConnection(host, port)
        try:
            conn.request("GET", prefix)
            response = conn.getresponse()
            if response.status == 200:
                break
        except OSError as e:
            if e.errno not in [61, 111]:
                raise
        time.sleep(sleep_amount)
    else:
        message = f"Test HTTP server on host {host} and port {port} did not return '200 OK' after {sleep_tries} tries"
        raise Exception(message)


def attempt_port(port: int) -> Optional[int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("", port))
        sock.close()
        return port
    except OSError:
        return None


def attempt_ports(port=None, set_galaxy_web_port=True) -> str:
    if port is not None:
        if not attempt_port(int(port)):
            raise Exception(f"An existing process seems bound to specified test server port [{port}]")
        return port
    else:
        random.seed()
        for _ in range(0, 9):
            port = attempt_port(random.randint(8000, 10000))
            if port:
                port = str(port)
                if set_galaxy_web_port:
                    os.environ["GALAXY_WEB_PORT"] = port
                return port

        raise Exception(f"Unable to open a port between {8000} and {10000} to start Galaxy server")


def uvicorn_serve(app, port, host=None):
    """Serve the webapp on a recommend port or a free one.

    Return the port the webapp is running on.
    """
    import asyncio

    from uvicorn.config import Config
    from uvicorn.server import Server

    access_log = False if "GALAXY_TEST_DISABLE_ACCESS_LOG" in os.environ else True
    config = Config(app, host=host, port=int(port), access_log=access_log)
    server = Server(config=config)

    def run_in_loop(loop):
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
            log.info("Event loop for uvicorn closed")

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=run_in_loop, args=(loop,))
    t.start()

    return server, port, t


def cleanup_directory(tempdir: str) -> None:
    """Clean up temporary files used by test unless GALAXY_TEST_NO_CLEANUP is set.

    Also respect TOOL_SHED_TEST_NO_CLEANUP for legacy reasons.
    """
    skip_cleanup = "GALAXY_TEST_NO_CLEANUP" in os.environ or "TOOL_SHED_TEST_NO_CLEANUP" in os.environ
    if skip_cleanup:
        log.info(f"GALAXY_TEST_NO_CLEANUP is on. Temporary files in {tempdir}")
        return
    try:
        if os.path.exists(tempdir) and not skip_cleanup:
            shutil.rmtree(tempdir)
    except Exception:
        pass


def build_galaxy_app(simple_kwargs) -> GalaxyUniverseApplication:
    """Build a Galaxy app object from a simple keyword arguments.

    Construct paste style complex dictionary and use load_app_properties so
    Galaxy override variables are respected. Also setup "global" references
    to sqlalchemy database context for Galaxy and install databases.
    """
    log.info("Galaxy database connection: %s", simple_kwargs["database_connection"])
    simple_kwargs["global_conf"] = get_webapp_global_conf()
    simple_kwargs["global_conf"]["__file__"] = "lib/galaxy/config/sample/galaxy.yml.sample"
    simple_kwargs = load_app_properties(kwds=simple_kwargs)
    # Build the Universe Application
    app = GalaxyUniverseApplication(**simple_kwargs, is_webapp=True)
    log.info("Embedded Galaxy application started")

    global install_context
    install_context = app.install_model.context

    # Toolbox indexing happens via the work queue out of band recently, and,
    # beyond potentially running async after tests execute doesn't execute
    # without building a webapp (app.is_webapp = False for this test kit).
    # We need to ensure to build an index for the test galaxy app -- this is
    # pretty fast with the limited toolset
    app.reindex_tool_search()

    return app


def explicitly_configured_host_and_port(prefix, config_object):
    host_env_key = f"{prefix}_TEST_HOST"
    port_env_key = f"{prefix}_TEST_PORT"
    port_random_env_key = f"{prefix}_TEST_PORT_RANDOM"
    default_web_host = getattr(config_object, "default_web_host", DEFAULT_WEB_HOST)
    host = os.environ.get(host_env_key, default_web_host)

    if os.environ.get(port_random_env_key, None) is not None:
        # Ignore the port environment variable, it wasn't explictly configured.
        port = None
    else:
        port = os.environ.get(port_env_key, None)

    # If an explicit port wasn't assigned for this test or test case, set this
    # environment variable so we know it is random. We can then randomly re-assign
    # for new tests.
    if port is None:
        os.environ["GALAXY_TEST_PORT_RANDOM"] = "1"
    else:
        os.environ["GALAXY_WEB_PORT"] = port

    return host, port


def set_and_wait_for_http_target(prefix, host, port, url_prefix, sleep_amount=0.1, sleep_tries=150):
    host_env_key = f"{prefix}_TEST_HOST"
    port_env_key = f"{prefix}_TEST_PORT"
    os.environ[host_env_key] = host
    os.environ[port_env_key] = port
    wait_for_http_server(host, port, url_prefix, sleep_amount=sleep_amount, sleep_tries=sleep_tries)


class ServerWrapper:
    def __init__(self, name, host, port, prefix=""):
        self.name = name
        self.host = host
        self.port = port
        self.prefix = prefix

    def get_logs(self) -> Optional[str]:
        # Subclasses can implement a way to return relevant logs
        pass

    @property
    def app(self):
        raise NotImplementedError("Test can be run against target - requires a Galaxy app object.")

    def stop(self) -> None:
        raise NotImplementedError()


class EmbeddedServerWrapper(ServerWrapper):
    def __init__(self, app, server, name, host, port, prefix="", thread=None):
        super().__init__(name, host, port, prefix)
        self._app = app
        self._server = server
        self._thread = thread

    @property
    def app(self):
        return self._app

    def stop(self):
        log.info(f"{threading.active_count()} threads were active before stopping embedded server")

        if self._server is not None and hasattr(self._server, "server_close"):
            log.info(f"Shutting down embedded {self.name} Paste server")
            self._server.server_close()
            log.info(f"Embedded web server {self.name} stopped")

        if self._server is not None and hasattr(self._server, "shutdown"):
            log.info(f"Shutting down embedded {self.name} uvicorn server")
            self._server.should_exit = True
            log.info(f"Embedded web server {self.name} stopped")

        if self._thread is not None:
            log.info("Stopping embedded server thread")
            self._thread.join()
            log.info("Embedded server thread stopped")

        if self._app is not None:
            log.info(f"Stopping application {self.name}")
            self._app.shutdown()
            log.info(f"Application {self.name} stopped.")

        thread_count = threading.active_count()
        log.info(f"{thread_count} active after stopping embedded server")


class GravityServerWrapper(ServerWrapper):
    def __init__(self, name, host, port, state_dir, stop_command):
        super().__init__(name, host, port)
        self.url_prefix = os.environ.get("GALAXY_CONFIG_GALAXY_URL_PREFIX", "/")
        self.state_dir = Path(state_dir)
        self.stop_command = stop_command

    def wait_for_server(self):
        try:
            set_and_wait_for_http_target(
                "GALAXY",
                self.host,
                self.port,
                url_prefix=self.url_prefix,
                sleep_amount=0.4,
            )
        except Exception:
            log.error("Gravity logs:\n%s", self.get_logs())

    def get_logs(self):
        gunicorn_logs = (self.state_dir / "log" / "gunicorn.log").read_text()
        gxit_logs = (self.state_dir / "log" / "gx-it-proxy.log").read_text()
        celery_logs = (self.state_dir / "log" / "celery.log").read_text()
        return f"Gunicorn logs:{os.linesep}{gunicorn_logs}{os.linesep}gx-it-proxy logs:{os.linesep}{gxit_logs}celery logs:{os.linesep}{celery_logs}"

    def stop(self):
        self.stop_command()


def launch_gravity(port, gxit_port=None, galaxy_config=None):
    galaxy_config = galaxy_config or {}
    if not gxit_port:
        gxit_port = attempt_ports(set_galaxy_web_port=False)
    if "interactivetools_proxy_host" not in galaxy_config:
        galaxy_config["interactivetools_proxy_host"] = f"localhost:{gxit_port}"
    # Can't use in-memory celery broker, just fall back to sqlalchemy
    celery_conf = galaxy_config.get("celery_conf", {})
    celery_conf.update({"broker_url": None})
    galaxy_config["celery_conf"] = celery_conf
    state_dir = tempfile.mkdtemp(suffix="state")
    config = {
        "gravity": {
            "log_dir": os.path.join(state_dir, "log"),
            "gunicorn": {"bind": f"localhost:{port}", "preload": "false"},
            "gx_it_proxy": {
                "enable": galaxy_config.get("interactivetools_enable", False),
                "port": gxit_port,
                "verbose": True,
                "sessions": galaxy_config.get("interactivetools_map"),
            },
        },
        "galaxy": galaxy_config,
    }
    with tempfile.NamedTemporaryFile("w", dir=state_dir, delete=False, suffix=".galaxy.yml") as config_fh:
        json.dump(config, config_fh)
    with tempfile.NamedTemporaryFile(delete=True) as socket:
        supervisord_socket = socket.name
    gravity_env = os.environ.copy()
    gravity_env["SUPERVISORD_SOCKET"] = supervisord_socket
    subprocess.check_output(["galaxyctl", "--config-file", config_fh.name, "update"], env=gravity_env)
    subprocess.check_output(["galaxyctl", "--config-file", config_fh.name, "start"], env=gravity_env)
    return state_dir, lambda: subprocess.check_output(
        ["galaxyctl", "--config-file", config_fh.name, "shutdown"], env=gravity_env
    )


def launch_server(
    app_factory,
    webapp_factory,
    prefix=DEFAULT_CONFIG_PREFIX,
    galaxy_config=None,
    config_object=None,
    init_fast_app=init_galaxy_fast_app,
):
    name = prefix.lower()
    host, port = explicitly_configured_host_and_port(prefix, config_object)
    port = attempt_ports(port)

    enable_realtime_mapping = getattr(config_object, "enable_realtime_mapping", False)
    if enable_realtime_mapping:
        interactive_tool_defaults = {
            "interactivetools_map": tempfile.NamedTemporaryFile(
                delete=False, suffix="interactivetools_map.sqlite"
            ).name,
            "interactivetools_enable": True,
            "interactivetools_upstream_proxy": False,
            "galaxy_infrastructure_url": f"http://localhost:{port}",
        }
        interactive_tool_defaults.update(galaxy_config or {})
        galaxy_config = interactive_tool_defaults

    if enable_realtime_mapping or os.environ.get("GALAXY_TEST_GRAVITY"):
        galaxy_config["root"] = galaxy_root
        state_dir, stop_command = launch_gravity(port=port, galaxy_config=galaxy_config)
        gravity_wrapper = GravityServerWrapper(name, host, port, state_dir, stop_command)
        gravity_wrapper.wait_for_server()
        return gravity_wrapper

    app = app_factory()
    url_prefix = getattr(app.config, f"{name}_url_prefix", "/")
    wsgi_webapp = webapp_factory(
        galaxy_config["global_conf"],
        app=app,
        use_translogger=False,
        static_enabled=True,
        register_shutdown_at_exit=False,
    )
    asgi_app = init_fast_app(wsgi_webapp, app)

    server, port, thread = uvicorn_serve(asgi_app, host=host, port=port)
    set_and_wait_for_http_target(prefix, host, port, url_prefix=url_prefix)
    log.debug(f"Embedded uvicorn web server for {name} started at {host}:{port}{url_prefix}")
    return EmbeddedServerWrapper(app, server, name, host, port, thread=thread, prefix=url_prefix)


class TestDriver:
    """Responsible for the life-cycle of a Galaxy-style functional test.

    Sets up servers, configures tests, and tears things
    down. This is somewhat like a Python TestCase - but different
    because it is meant to provide a main() endpoint.
    """

    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self):
        """Setup tracked resources."""
        self.server_wrappers: List[ServerWrapper] = []
        self.temp_directories: List[str] = []

    def setup(self) -> None:
        """Called before tests are built."""

    def tear_down(self) -> None:
        """Cleanup resources tracked by this object."""
        self.stop_servers()
        for temp_directory in self.temp_directories:
            cleanup_directory(temp_directory)

    def stop_servers(self) -> None:
        for server_wrapper in self.server_wrappers:
            server_wrapper.stop()
        for th in threading.enumerate():
            log.debug(f"After stopping all servers thread {th} is alive.")
        if (active_count := threading.active_count()) > 100:
            # For an unknown reason running iRODS tests results in application threads not shutting down immediately,
            # but if we've accumulated over 100 active threads something else is wrong that needs to be fixed.
            raise Exception(
                f"{active_count} active threads after stopping embedded server. Have all threads been shut down?"
            )
        self.server_wrappers = []

    def mkdtemp(self) -> str:
        """Return a temp directory that is properly cleaned up or not based on the config."""
        temp_directory = tempfile.mkdtemp()
        self.temp_directories.append(temp_directory)
        return temp_directory


class GalaxyTestDriver(TestDriver):
    """Instantial a Galaxy-style TestDriver for testing Galaxy."""

    testing_shed_tools = False

    def _configure(self, config_object=None) -> None:
        """Setup various variables used to launch a Galaxy server."""
        config_object = self._ensure_config_object(config_object)
        self.external_galaxy = os.environ.get("GALAXY_TEST_EXTERNAL", None)
        if not self.external_galaxy:
            os.environ["GALAXY_TEST_STRICT_CHECKS"] = "1"

        # Allow controlling the log format
        self.log_format = os.environ.get("GALAXY_TEST_LOG_FORMAT")

        self.galaxy_test_tmp_dir = get_galaxy_test_tmp_dir()
        self.temp_directories.append(self.galaxy_test_tmp_dir)

        self.testing_shed_tools = getattr(config_object, "testing_shed_tools", False)

        default_tool_conf: Optional[str]
        datatypes_conf_override: Optional[str]
        framework_tools_and_types = getattr(config_object, "framework_tool_and_types", False)
        if framework_tools_and_types:
            default_tool_conf = FRAMEWORK_SAMPLE_TOOLS_CONF
            datatypes_conf_override = FRAMEWORK_DATATYPES_CONF
        else:
            default_tool_conf = getattr(config_object, "default_tool_conf", None)
            datatypes_conf_override = getattr(config_object, "datatypes_conf_override", None)
        allow_tool_conf_override = getattr(config_object, "allow_tool_conf_override", True)
        self.allow_tool_conf_override = allow_tool_conf_override
        self.default_tool_conf = default_tool_conf
        self.datatypes_conf_override = datatypes_conf_override

    def setup(self, config_object=None):
        """Setup a Galaxy server for functional test (if needed).

        Configuration options can be specified as attributes on the supplied
        ```config_object``` (defaults to self).
        """
        self._saved_galaxy_config = None
        self._configure(config_object)
        self._register_and_run_servers(config_object)

    def get_logs(self) -> Optional[str]:
        if not self.server_wrappers:
            return None
        server_wrapper = self.server_wrappers[0]
        return server_wrapper.get_logs()

    def restart(self, config_object=None, handle_config=None) -> None:
        self.stop_servers()
        self._register_and_run_servers(config_object, handle_config=handle_config)

    def _register_and_run_servers(self, config_object=None, handle_config=None) -> None:
        config_object = self._ensure_config_object(config_object)
        self.app: Optional[GalaxyUniverseApplication] = None

        if self.external_galaxy is None:
            if self._saved_galaxy_config is not None:
                galaxy_config = self._saved_galaxy_config
            else:
                tempdir = tempfile.mkdtemp(dir=self.galaxy_test_tmp_dir)
                # Configure the database path.
                galaxy_db_path = database_files_path(tempdir)
                # Allow config object to specify a config dict or a method to produce
                # one - other just read the properties above and use the default
                # implementation from this file.
                galaxy_config = getattr(config_object, "galaxy_config", None)
                if callable(galaxy_config):
                    galaxy_config = galaxy_config()
                if galaxy_config is None:
                    galaxy_config = setup_galaxy_config(
                        galaxy_db_path,
                        use_test_file_dir=not self.testing_shed_tools,
                        default_install_db_merged=True,
                        default_tool_conf=self.default_tool_conf,
                        datatypes_conf=self.datatypes_conf_override,
                        prefer_template_database=getattr(config_object, "prefer_template_database", False),
                        log_format=self.log_format,
                        conda_auto_init=getattr(config_object, "conda_auto_init", False),
                        conda_auto_install=getattr(config_object, "conda_auto_install", False),
                        use_shared_connection_for_amqp=getattr(config_object, "use_shared_connection_for_amqp", False),
                        allow_tool_conf_override=self.allow_tool_conf_override,
                        allow_path_paste=getattr(config_object, "allow_path_paste", False),
                    )

                    isolate_galaxy_config = getattr(config_object, "isolate_galaxy_config", False)
                    if isolate_galaxy_config:
                        galaxy_config["config_dir"] = tempdir

                    self._saved_galaxy_config = galaxy_config

            if galaxy_config is not None:
                handle_galaxy_config_kwds = handle_config or getattr(config_object, "handle_galaxy_config_kwds", None)
                if handle_galaxy_config_kwds is not None:
                    handle_galaxy_config_kwds(galaxy_config)

            server_wrapper = launch_server(
                app_factory=lambda: self.build_galaxy_app(galaxy_config),
                webapp_factory=lambda *args, **kwd: buildapp.app_factory(*args, wsgi_preflight=False, **kwd),
                galaxy_config=galaxy_config,
                config_object=config_object,
            )
            self.server_wrappers.append(server_wrapper)
        else:
            log.info(f"Functional tests will be run against test external Galaxy server {self.external_galaxy}")
            # Ensure test file directory setup even though galaxy config isn't built.
            ensure_test_file_dir_set()

    def build_galaxy_app(self, galaxy_config) -> GalaxyUniverseApplication:
        self.app = build_galaxy_app(galaxy_config)
        return self.app

    def _ensure_config_object(self, config_object):
        if config_object is None:
            config_object = self
        return config_object

    def run_tool_test(
        self, tool_id: str, index: int = 0, resource_parameters: Optional[Dict[str, Any]] = None, **kwd
    ) -> None:
        if resource_parameters is None:
            resource_parameters = {}
        _, _, url = target_url_parts()
        galaxy_interactor_kwds = {
            "galaxy_url": url,
            "master_api_key": get_admin_api_key(),
            "api_key": get_user_api_key(),
            "keep_outputs_dir": None,
        }
        galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
        verify_tool(
            tool_id=tool_id,
            test_index=index,
            galaxy_interactor=galaxy_interactor,
            resource_parameters=resource_parameters,
            **kwd,
        )


def drive_test(test_driver_class):
    """Instantiate driver class, run, and exit appropriately."""
    test_driver = test_driver_class()
    sys.exit(test_driver.run())


__all__ = (
    "copy_database_template",
    "build_logger",
    "drive_test",
    "FRAMEWORK_UPLOAD_TOOL_CONF",
    "FRAMEWORK_SAMPLE_TOOLS_CONF",
    "FRAMEWORK_DATATYPES_CONF",
    "database_conf",
    "get_webapp_global_conf",
    "setup_galaxy_config",
    "TestDriver",
    "wait_for_http_server",
)
