"""Scripts for drivers of Galaxy functional tests."""

import fcntl
import logging
import os
import random
import shutil
import signal
import socket
import string
import struct
import subprocess
import sys
import tempfile
import threading
import time

import nose.config
import nose.core
import nose.loader
import nose.plugins.manager
from paste import httpserver
from six.moves import (
    http_client,
    shlex_quote
)
from six.moves.urllib.parse import urlparse
from sqlalchemy_utils import (
    create_database,
    database_exists,
)

from galaxy.app import UniverseApplication as GalaxyUniverseApplication
from galaxy.config import LOGGING_CONFIG_DEFAULT
from galaxy.model import mapping
from galaxy.model.tool_shed_install import mapping as toolshed_mapping
from galaxy.tools.verify.interactor import GalaxyInteractorApi, verify_tool
from galaxy.util import asbool, download_to_file
from galaxy.util.properties import load_app_properties
from galaxy.web import buildapp
from galaxy.webapps.tool_shed.app import UniverseApplication as ToolshedUniverseApplication
from .api_util import get_master_api_key, get_user_api_key
from .instrument import StructuredTestDataPlugin
from .nose_util import run
from .test_logging import logging_config_file

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
DEFAULT_WEB_HOST = socket.gethostbyname('localhost')
DEFAULT_CONFIG_PREFIX = "GALAXY"
GALAXY_TEST_DIRECTORY = os.path.join(galaxy_root, "test")
GALAXY_TEST_FILE_DIR = "test-data,https://github.com/galaxyproject/galaxy-test-data.git"
TOOL_SHED_TEST_DATA = os.path.join(GALAXY_TEST_DIRECTORY, "shed_functional", "test_data")
TEST_WEBHOOKS_DIR = os.path.join(galaxy_root, "test", "functional", "webhooks")
FRAMEWORK_TOOLS_DIR = os.path.join(GALAXY_TEST_DIRECTORY, "functional", "tools")
FRAMEWORK_UPLOAD_TOOL_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "upload_tool_conf.xml")
FRAMEWORK_SAMPLE_TOOLS_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "samples_tool_conf.xml")
FRAMEWORK_DATATYPES_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "sample_datatypes_conf.xml")
MIGRATED_TOOL_PANEL_CONFIG = 'config/migrated_tools_conf.xml'
INSTALLED_TOOL_PANEL_CONFIGS = [
    os.environ.get('GALAXY_TEST_SHED_TOOL_CONF', 'config/shed_tool_conf.xml')
]

DEFAULT_LOCALES = "en"

log = logging.getLogger("test_driver")


# Global variables to pass database contexts around - only needed for older
# Tool Shed twill tests that didn't utilize the API for such interactions.
galaxy_context = None
tool_shed_context = None
install_context = None


def setup_tool_shed_tmp_dir():
    tool_shed_test_tmp_dir = os.environ.get('TOOL_SHED_TEST_TMP_DIR', None)
    if tool_shed_test_tmp_dir is None:
        tool_shed_test_tmp_dir = tempfile.mkdtemp()
    # Here's the directory where everything happens.  Temporary directories are created within this directory to contain
    # the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
    # the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
    os.environ['TOOL_SHED_TEST_TMP_DIR'] = tool_shed_test_tmp_dir
    return tool_shed_test_tmp_dir


def get_galaxy_test_tmp_dir():
    """Create test directory for use by Galaxy server being setup for testing."""
    galaxy_test_tmp_dir = os.environ.get('GALAXY_TEST_TMP_DIR', None)
    if galaxy_test_tmp_dir is None:
        galaxy_test_tmp_dir = tempfile.mkdtemp()
    return galaxy_test_tmp_dir


def configure_environment():
    """Hack up environment for test cases."""
    # no op remove if unused
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ['HTTP_ACCEPT_LANGUAGE'] = DEFAULT_LOCALES

    # Used by get_filename in tool shed's twilltestcase.
    if "TOOL_SHED_TEST_FILE_DIR" not in os.environ:
        os.environ["TOOL_SHED_TEST_FILE_DIR"] = TOOL_SHED_TEST_DATA

    os.environ["GALAXY_TEST_ENVIRONMENT_CONFIGURED"] = "1"


def build_logger():
    """Build a logger for test driver script."""
    return log


def ensure_test_file_dir_set():
    """Ensure GALAXY_TEST_FILE_DIR setup in environment for test data resolver.

    Return first directory for backward compat.
    """
    galaxy_test_file_dir = os.environ.get('GALAXY_TEST_FILE_DIR', GALAXY_TEST_FILE_DIR)
    os.environ['GALAXY_TEST_FILE_DIR'] = galaxy_test_file_dir
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
    conda_auto_install=False
):
    """Setup environment and build config for test Galaxy instance."""
    # For certain docker operations this needs to be evaluated out - e.g. for cwltool.
    tmpdir = os.path.realpath(tmpdir)
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    file_path = os.path.join(tmpdir, 'files')
    template_cache_path = tempfile.mkdtemp(prefix='compiled_templates_', dir=tmpdir)
    new_file_path = tempfile.mkdtemp(prefix='new_files_path_', dir=tmpdir)
    job_working_directory = tempfile.mkdtemp(prefix='job_working_directory_', dir=tmpdir)

    if use_test_file_dir:
        first_test_file_dir = ensure_test_file_dir_set()
        if not os.path.isabs(first_test_file_dir):
            first_test_file_dir = os.path.join(galaxy_root, first_test_file_dir)
        library_import_dir = first_test_file_dir
        import_dir = os.path.join(first_test_file_dir, 'users')
        if os.path.exists(import_dir):
            user_library_import_dir = import_dir
        else:
            user_library_import_dir = None
    else:
        user_library_import_dir = None
        library_import_dir = None
    job_config_file = os.environ.get('GALAXY_TEST_JOB_CONFIG_FILE', default_job_config_file)
    tool_path = os.environ.get('GALAXY_TEST_TOOL_PATH', 'tools')
    tool_dependency_dir = os.environ.get('GALAXY_TOOL_DEPENDENCY_DIR', None)
    if tool_dependency_dir is None:
        tool_dependency_dir = tempfile.mkdtemp(dir=tmpdir, prefix="tool_dependencies")
    tool_data_table_config_path = _tool_data_table_config_path(default_tool_data_table_config_path)
    default_data_manager_config = 'config/data_manager_conf.xml.sample'
    for data_manager_config in ['config/data_manager_conf.xml', 'data_manager_conf.xml']:
        if os.path.exists(data_manager_config):
            default_data_manager_config = data_manager_config
    data_manager_config_file = "%s,test/functional/tools/sample_data_manager_conf.xml" % default_data_manager_config
    master_api_key = get_master_api_key()

    # Data Manager testing temp path
    # For storing Data Manager outputs and .loc files so that real ones don't get clobbered
    galaxy_data_manager_data_path = tempfile.mkdtemp(prefix='data_manager_tool-data', dir=tmpdir)

    tool_conf = os.environ.get('GALAXY_TEST_TOOL_CONF', default_tool_conf)
    conda_auto_install = os.environ.get('GALAXY_TEST_CONDA_AUTO_INSTALL', conda_auto_install)
    conda_auto_init = os.environ.get('GALAXY_TEST_CONDA_AUTO_INIT', conda_auto_init)
    conda_prefix = os.environ.get('GALAXY_TEST_CONDA_PREFIX')
    if tool_conf is None:
        # As a fallback always at least allow upload.
        tool_conf = FRAMEWORK_UPLOAD_TOOL_CONF

    if shed_tool_conf is not None:
        tool_conf = "%s,%s" % (tool_conf, shed_tool_conf)

    shed_tool_data_table_config = default_shed_tool_data_table_config
    if shed_tool_data_table_config is None:
        shed_tool_data_table_config = 'config/shed_tool_data_table_conf.xml'

    config = dict(
        admin_users='test@bx.psu.edu',
        allow_library_path_paste=True,
        allow_user_creation=True,
        allow_user_deletion=True,
        api_allow_run_as='test@bx.psu.edu',
        auto_configure_logging=logging_config_file is None,
        check_migrate_tools=False,
        chunk_upload_size=100,
        conda_prefix=conda_prefix,
        conda_auto_init=conda_auto_init,
        conda_auto_install=conda_auto_install,
        cleanup_job='onsuccess',
        data_manager_config_file=data_manager_config_file,
        enable_beta_tool_formats=True,
        enable_beta_workflow_format=True,
        expose_dataset_path=True,
        file_path=file_path,
        ftp_upload_purge=False,
        galaxy_data_manager_data_path=galaxy_data_manager_data_path,
        id_secret='changethisinproductiontoo',
        job_config_file=job_config_file,
        job_working_directory=job_working_directory,
        library_import_dir=library_import_dir,
        log_destination="stdout",
        new_file_path=new_file_path,
        override_tempdir=False,
        master_api_key=master_api_key,
        running_functional_tests=True,
        shed_tool_data_table_config=shed_tool_data_table_config,
        template_cache_path=template_cache_path,
        template_path='templates',
        tool_config_file=tool_conf,
        tool_data_table_config_path=tool_data_table_config_path,
        tool_parse_help=False,
        tool_path=tool_path,
        update_integrated_tool_panel=update_integrated_tool_panel,
        use_tasked_jobs=True,
        use_heartbeat=False,
        user_library_import_dir=user_library_import_dir,
        webhooks_dir=TEST_WEBHOOKS_DIR,
        logging=LOGGING_CONFIG_DEFAULT,
        monitor_thread_join_timeout=5,
        object_store_store_by="uuid",
    )
    config.update(database_conf(tmpdir, prefer_template_database=prefer_template_database))
    config.update(install_database_conf(tmpdir, default_merged=default_install_db_merged))
    if datatypes_conf is not None:
        config['datatypes_config_file'] = datatypes_conf
    if enable_tool_shed_check:
        config["enable_tool_shed_check"] = enable_tool_shed_check
        config["hours_between_check"] = 0.001
    if tool_dependency_dir:
        config["tool_dependency_dir"] = tool_dependency_dir
        # Used by shed's twill dependency stuff - todo read from
        # Galaxy's config API.
        os.environ["GALAXY_TEST_TOOL_DEPENDENCY_DIR"] = tool_dependency_dir
    return config


def _tool_data_table_config_path(default_tool_data_table_config_path=None):
    tool_data_table_config_path = os.environ.get('GALAXY_TEST_TOOL_DATA_TABLE_CONF', default_tool_data_table_config_path)
    if tool_data_table_config_path is None:
        # ... otherise find whatever Galaxy would use as the default and
        # the sample data for fucntional tests to that.
        default_tool_data_config = 'config/tool_data_table_conf.xml.sample'
        for tool_data_config in ['config/tool_data_table_conf.xml', 'tool_data_table_conf.xml']:
            if os.path.exists(tool_data_config):
                default_tool_data_config = tool_data_config
        tool_data_table_config_path = '%s,test/functional/tool-data/sample_tool_data_tables.xml' % default_tool_data_config
    return tool_data_table_config_path


def nose_config_and_run(argv=None, env=None, ignore_files=[], plugins=None):
    """Setup a nose context and run tests.

    Tests are specified by argv (defaulting to sys.argv).
    """
    if env is None:
        env = os.environ
    if plugins is None:
        plugins = nose.plugins.manager.DefaultPluginManager()
    if argv is None:
        argv = sys.argv

    test_config = nose.config.Config(
        env=os.environ,
        ignoreFiles=ignore_files,
        plugins=plugins,
    )

    # Add custom plugin to produce JSON data used by planemo.
    test_config.plugins.addPlugin(StructuredTestDataPlugin())
    test_config.configure(argv)

    result = run(test_config)

    success = result.wasSuccessful()
    return success


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
        raise Exception("Failed to copy database template from source %s" % source)


def database_conf(db_path, prefix="GALAXY", prefer_template_database=False):
    """Find (and populate if needed) Galaxy database connection."""
    database_auto_migrate = False
    check_migrate_databases = True
    dburi_var = "%s_TEST_DBURI" % prefix
    template_name = None
    if dburi_var in os.environ:
        database_connection = os.environ[dburi_var]
        # only template if postgres - not mysql or sqlite
        do_template = prefer_template_database and database_connection.startswith("p")
        if do_template:
            database_template_parsed = urlparse(database_connection)
            template_name = database_template_parsed.path[1:]  # drop / from /galaxy
            actual_db = "gxtest" + ''.join(random.choice(string.ascii_uppercase) for _ in range(10))
            actual_database_parsed = database_template_parsed._replace(path="/%s" % actual_db)
            database_connection = actual_database_parsed.geturl()
            if not database_exists(database_connection):
                # We pass by migrations and instantiate the current table
                create_database(database_connection)
                mapping.init('/tmp', database_connection, create_tables=True, map_install_models=True)
                toolshed_mapping.init(database_connection, create_tables=True)
                check_migrate_databases = False
    else:
        default_db_filename = "%s.sqlite" % prefix.lower()
        template_var = "%s_TEST_DB_TEMPLATE" % prefix
        db_path = os.path.join(db_path, default_db_filename)
        if template_var in os.environ:
            # Middle ground between recreating a completely new
            # database and pointing at existing database with
            # GALAXY_TEST_DBURI. The former requires a lot of setup
            # time, the latter results in test failures in certain
            # cases (namely tool shed tests expecting clean database).
            copy_database_template(os.environ[template_var], db_path)
            database_auto_migrate = True
        database_connection = 'sqlite:///%s' % db_path
    config = {
        "check_migrate_databases": check_migrate_databases,
        "database_connection": database_connection,
        "database_auto_migrate": database_auto_migrate
    }
    if not database_connection.startswith("sqlite://"):
        config["database_engine_option_max_overflow"] = "20"
        config["database_engine_option_pool_size"] = "10"
    if template_name:
        config["database_template"] = template_name
    return config


def install_database_conf(db_path, default_merged=False):
    if 'GALAXY_TEST_INSTALL_DBURI' in os.environ:
        install_galaxy_database_connection = os.environ['GALAXY_TEST_INSTALL_DBURI']
    elif asbool(os.environ.get('GALAXY_TEST_INSTALL_DB_MERGED', default_merged)):
        install_galaxy_database_connection = None
    else:
        install_galaxy_db_path = os.path.join(db_path, 'install.sqlite')
        install_galaxy_database_connection = 'sqlite:///%s' % install_galaxy_db_path
    conf = {}
    if install_galaxy_database_connection is not None:
        conf["install_database_connection"] = install_galaxy_database_connection
    return conf


def database_files_path(test_tmpdir, prefix="GALAXY"):
    """Create a mock database/ directory like in GALAXY_ROOT.

    Use prefix to default this if TOOL_SHED_TEST_DBPATH or
    GALAXY_TEST_DBPATH is set in the environment.
    """
    environ_var = "%s_TEST_DBPATH" % prefix
    if environ_var in os.environ:
        db_path = os.environ[environ_var]
    else:
        tempdir = tempfile.mkdtemp(dir=test_tmpdir)
        db_path = os.path.join(tempdir, 'database')
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
        static_images_dir=os.path.join(static_dir, 'images', ''),
        static_favicon_dir=os.path.join(static_dir, 'favicon.ico'),
        static_scripts_dir=os.path.join(static_dir, 'scripts', ''),
        static_style_dir=os.path.join(static_dir, 'style', 'blue'),
        static_robots_txt=os.path.join(static_dir, 'robots.txt'),
    )


def get_webapp_global_conf():
    """Get the global_conf dictionary sent to ``app_factory``."""
    # (was originally sent 'dict()') - nothing here for now except static settings
    global_conf = dict()
    global_conf.update(_get_static_settings())
    return global_conf


def wait_for_http_server(host, port, sleep_amount=0.1, sleep_tries=150):
    """Wait for an HTTP server to boot up."""
    # Test if the server is up
    for i in range(sleep_tries):
        # directly test the app, not the proxy
        conn = http_client.HTTPConnection(host, port)
        try:
            conn.request("GET", "/")
            response = conn.getresponse()
            if response.status == 200:
                break
        except socket.error as e:
            if e.errno not in [61, 111]:
                raise
        time.sleep(sleep_amount)
    else:
        template = "Test HTTP server on host %s and port %s did not return '200 OK' after 10 tries"
        message = template % (host, port)
        raise Exception(message)


def attempt_ports(port):
    if port is not None:
        yield port

        raise Exception("An existing process seems bound to specified test server port [%s]" % port)
    else:
        random.seed()
        for i in range(0, 9):
            port = str(random.randint(8000, 10000))
            yield port

        raise Exception("Unable to open a port between %s and %s to start Galaxy server" % (8000, 10000))


def serve_webapp(webapp, port=None, host=None):
    """Serve the webapp on a recommend port or a free one.

    Return the port the webapp is running on.
    """
    server = None
    for port in attempt_ports(port):
        try:
            server = httpserver.serve(webapp, host=host, port=port, start_loop=False)
            break
        except socket.error as e:
            if e[0] == 98:
                continue
            raise

    t = threading.Thread(target=server.serve_forever)
    t.start()

    return server, port


def cleanup_directory(tempdir):
    """Clean up temporary files used by test unless GALAXY_TEST_NO_CLEANUP is set.

    Also respect TOOL_SHED_TEST_NO_CLEANUP for legacy reasons.
    """
    skip_cleanup = "GALAXY_TEST_NO_CLEANUP" in os.environ or "TOOL_SHED_TEST_NO_CLEANUP" in os.environ
    if skip_cleanup:
        log.info("GALAXY_TEST_NO_CLEANUP is on. Temporary files in %s" % tempdir)
        return
    try:
        if os.path.exists(tempdir) and not skip_cleanup:
            shutil.rmtree(tempdir)
    except Exception:
        pass


def setup_shed_tools_for_test(app, tmpdir, testing_migrated_tools, testing_installed_tools):
    """Modify Galaxy app's toolbox for migrated or installed tool tests."""
    if testing_installed_tools:
        # TODO: Do this without modifying app - that is a pretty violation
        # of Galaxy's abstraction - we shouldn't require app at all let alone
        # be modifying it.

        tool_configs = app.config.tool_configs
        # Eliminate the migrated_tool_panel_config from the app's tool_configs, append the list of installed_tool_panel_configs,
        # and reload the app's toolbox.
        relative_migrated_tool_panel_config = os.path.join(app.config.root, MIGRATED_TOOL_PANEL_CONFIG)
        if relative_migrated_tool_panel_config in tool_configs:
            tool_configs.remove(relative_migrated_tool_panel_config)
        for installed_tool_panel_config in INSTALLED_TOOL_PANEL_CONFIGS:
            tool_configs.append(installed_tool_panel_config)
        from galaxy import tools  # delay import because this brings in so many modules for small tests # noqa: E402
        app.toolbox = tools.ToolBox(tool_configs, app.config.tool_path, app)


def build_galaxy_app(simple_kwargs):
    """Build a Galaxy app object from a simple keyword arguments.

    Construct paste style complex dictionary and use load_app_properties so
    Galaxy override variables are respected. Also setup "global" references
    to sqlalchemy database context for Galaxy and install databases.
    """
    log.info("Galaxy database connection: %s", simple_kwargs["database_connection"])
    simple_kwargs['global_conf'] = get_webapp_global_conf()
    simple_kwargs['global_conf']['__file__'] = "config/galaxy.yml.sample"
    simple_kwargs = load_app_properties(
        kwds=simple_kwargs
    )
    # Build the Universe Application
    app = GalaxyUniverseApplication(**simple_kwargs)
    log.info("Embedded Galaxy application started")

    global galaxy_context
    global install_context
    galaxy_context = app.model.context
    install_context = app.install_model.context

    return app


def build_shed_app(simple_kwargs):
    """Build a Galaxy app object from a simple keyword arguments.

    Construct paste style complex dictionary. Also setup "global" reference
    to sqlalchemy database context for tool shed database.
    """
    log.info("Tool shed database connection: %s", simple_kwargs["database_connection"])
    # TODO: Simplify global_conf to match Galaxy above...
    simple_kwargs['__file__'] = 'tool_shed_wsgi.yml.sample'
    simple_kwargs['global_conf'] = get_webapp_global_conf()

    app = ToolshedUniverseApplication(**simple_kwargs)
    log.info("Embedded Toolshed application started")

    global tool_shed_context
    tool_shed_context = app.model.context

    return app


class classproperty(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15].encode('utf-8'))
    )[20:24])


def explicitly_configured_host_and_port(prefix, config_object):
    host_env_key = "%s_TEST_HOST" % prefix
    port_env_key = "%s_TEST_PORT" % prefix
    port_random_env_key = "%s_TEST_PORT_RANDOM" % prefix
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

    return host, port


def set_and_wait_for_http_target(prefix, host, port, sleep_amount=0.1, sleep_tries=150):
    host_env_key = "%s_TEST_HOST" % prefix
    port_env_key = "%s_TEST_PORT" % prefix
    os.environ[host_env_key] = host
    os.environ[port_env_key] = port
    wait_for_http_server(host, port, sleep_amount=sleep_amount, sleep_tries=sleep_tries)


class ServerWrapper(object):

    def __init__(self, name, host, port):
        self.name = name
        self.host = host
        self.port = port

    @property
    def app(self):
        raise NotImplementedError("Test can be run against target - requires a Galaxy app object.")

    def stop(self):
        raise NotImplementedError()


class PasteServerWrapper(ServerWrapper):

    def __init__(self, app, server, name, host, port):
        super(PasteServerWrapper, self).__init__(name, host, port)
        self._app = app
        self._server = server

    @property
    def app(self):
        return self._app

    def stop(self):
        if self._server is not None:
            log.info("Shutting down embedded %s web server" % self.name)
            self._server.server_close()
            log.info("Embedded web server %s stopped" % self.name)

        if self._app is not None:
            log.info("Stopping application %s" % self.name)
            self._app.shutdown()
            log.info("Application %s stopped." % self.name)


class UwsgiServerWrapper(ServerWrapper):

    def __init__(self, p, name, host, port):
        super(UwsgiServerWrapper, self).__init__(name, host, port)
        self._p = p
        self._r = None
        self._t = threading.Thread(target=self.wait)
        self._t.start()

    def __del__(self):
        self._t.join()

    def wait(self):
        self._r = self._p.wait()

    def stop(self):
        try:
            os.killpg(os.getpgid(self._p.pid), signal.SIGTERM)
        except Exception:
            pass
        time.sleep(.1)
        try:
            os.killpg(os.getpgid(self._p.pid), signal.SIGKILL)
        except Exception:
            pass
        self._t.join()


def launch_uwsgi(kwargs, tempdir, prefix=DEFAULT_CONFIG_PREFIX, config_object=None):
    name = prefix.lower()

    host, port = explicitly_configured_host_and_port(prefix, config_object)

    config = {}
    config["galaxy"] = kwargs.copy()

    yaml_config_path = os.path.join(tempdir, "galaxy.yml")
    with open(yaml_config_path, "w") as f:
        import yaml
        yaml.dump(config, f)

    def attempt_port_bind(port):
        uwsgi_command = [
            "uwsgi",
            "--http",
            "%s:%s" % (host, port),
            "--yaml",
            yaml_config_path,
            "--module",
            "galaxy.webapps.galaxy.buildapp:uwsgi_app_factory()",
            "--enable-threads",
            "--die-on-term",
        ]
        for p in sys.path:
            uwsgi_command.append('--pythonpath')
            uwsgi_command.append(p)

        handle_uwsgi_cli_command = getattr(
            config_object, "handle_uwsgi_cli_command", None
        )
        if handle_uwsgi_cli_command is not None:
            handle_uwsgi_cli_command(uwsgi_command)

        # we don't want to quote every argument but we don't want to print unquoted ones either, so do this
        log.info("Starting uwsgi with command line: %s", ' '.join([shlex_quote(x) for x in uwsgi_command]))
        p = subprocess.Popen(
            uwsgi_command,
            cwd=galaxy_root,
            preexec_fn=os.setsid,
        )
        return UwsgiServerWrapper(
            p, name, host, port
        )

    for port in attempt_ports(port):
        server_wrapper = attempt_port_bind(port)
        try:
            set_and_wait_for_http_target(prefix, host, port, sleep_tries=50)
            log.info("Test-managed uwsgi web server for %s started at %s:%s" % (name, host, port))
            return server_wrapper
        except Exception:
            server_wrapper.stop()


def launch_server(app, webapp_factory, kwargs, prefix=DEFAULT_CONFIG_PREFIX, config_object=None):
    """Launch a web server for a given app using supplied factory.

    Consistently read either GALAXY_TEST_HOST and GALAXY_TEST_PORT or
    TOOL_SHED_TEST_HOST and TOOL_SHED_TEST_PORT and ensure these are
    all set after this method has been called.
    """
    name = prefix.lower()

    host, port = explicitly_configured_host_and_port(prefix, config_object)

    webapp = webapp_factory(
        kwargs['global_conf'],
        app=app,
        use_translogger=False,
        static_enabled=True
    )
    server, port = serve_webapp(
        webapp,
        host=host, port=port
    )
    set_and_wait_for_http_target(prefix, host, port)
    log.info("Embedded paste web server for %s started at %s:%s" % (name, host, port))
    return PasteServerWrapper(
        app, server, name, host, port
    )


class TestDriver(object):
    """Responsible for the life-cycle of a Galaxy-style functional test.

    Sets up servers, configures tests, runs nose, and tears things
    down. This is somewhat like a Python TestCase - but different
    because it is meant to provide a main() endpoint.
    """

    def __init__(self):
        """Setup tracked resources."""
        self.server_wrappers = []
        self.temp_directories = []

    def setup(self):
        """Called before tests are built."""

    def build_tests(self):
        """After environment is setup, setup nose tests."""

    def tear_down(self):
        """Cleanup resources tracked by this object."""
        self.stop_servers()
        for temp_directory in self.temp_directories:
            cleanup_directory(temp_directory)

    def stop_servers(self):
        for server_wrapper in self.server_wrappers:
            server_wrapper.stop()
        self.server_wrappers = []

    def mkdtemp(self):
        """Return a temp directory that is properly cleaned up or not based on the config."""
        temp_directory = tempfile.mkdtemp()
        self.temp_directories.append(temp_directory)
        return temp_directory

    def run(self):
        """Driver whole test.

        Setup environment, build tests (if needed), run test,
        and finally cleanup resources.
        """
        configure_environment()
        self.setup()
        self.build_tests()
        try:
            success = nose_config_and_run()
            return 0 if success else 1
        except Exception as e:
            log.info("Failure running tests")
            raise e
        finally:
            log.info("Shutting down")
            self.tear_down()


class GalaxyTestDriver(TestDriver):
    """Instantial a Galaxy-style nose TestDriver for testing Galaxy."""

    testing_shed_tools = False

    def _configure(self, config_object=None):
        """Setup various variables used to launch a Galaxy server."""
        config_object = self._ensure_config_object(config_object)
        self.external_galaxy = os.environ.get('GALAXY_TEST_EXTERNAL', None)

        # Allow a particular test to force uwsgi or any test to use uwsgi with
        # the GALAXY_TEST_UWSGI environment variable.
        use_uwsgi = os.environ.get('GALAXY_TEST_UWSGI', None)
        if not use_uwsgi:
            if getattr(config_object, "require_uwsgi", None):
                use_uwsgi = True
        self.use_uwsgi = use_uwsgi

        # Allow controlling the log format
        log_format = os.environ.get('GALAXY_TEST_LOG_FORMAT', None)
        if not log_format and use_uwsgi:
            log_format = "%(name)s %(levelname)-5.5s %(asctime)s " \
                         "[p:%(process)s,w:%(worker_id)s,m:%(mule_id)s] " \
                         "[%(threadName)s] %(message)s"

        self.log_format = log_format

        self.galaxy_test_tmp_dir = get_galaxy_test_tmp_dir()
        self.temp_directories.append(self.galaxy_test_tmp_dir)

        self.testing_shed_tools = getattr(config_object, "testing_shed_tools", False)

        if getattr(config_object, "framework_tool_and_types", False):
            default_tool_conf = FRAMEWORK_SAMPLE_TOOLS_CONF
            datatypes_conf_override = FRAMEWORK_DATATYPES_CONF
        else:
            default_tool_conf = getattr(config_object, "default_tool_conf", None)
            datatypes_conf_override = getattr(config_object, "datatypes_conf_override", None)

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

    def restart(self, config_object=None, handle_config=None):
        self.stop_servers()
        self._register_and_run_servers(config_object, handle_config=handle_config)

    def _register_and_run_servers(self, config_object=None, handle_config=None):
        config_object = self._ensure_config_object(config_object)
        self.app = None

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
                if hasattr(galaxy_config, '__call__'):
                    galaxy_config = galaxy_config()
                if galaxy_config is None:
                    setup_galaxy_config_kwds = dict(
                        use_test_file_dir=not self.testing_shed_tools,
                        default_install_db_merged=True,
                        default_tool_conf=self.default_tool_conf,
                        datatypes_conf=self.datatypes_conf_override,
                        prefer_template_database=getattr(config_object, "prefer_template_database", False),
                        log_format=self.log_format,
                        conda_auto_init=getattr(config_object, "conda_auto_init", False),
                        conda_auto_install=getattr(config_object, "conda_auto_install", False),
                    )
                    galaxy_config = setup_galaxy_config(
                        galaxy_db_path,
                        **setup_galaxy_config_kwds
                    )
                    self._saved_galaxy_config = galaxy_config

            if galaxy_config is not None:
                handle_galaxy_config_kwds = handle_config or getattr(
                    config_object, "handle_galaxy_config_kwds", None
                )
                if handle_galaxy_config_kwds is not None:
                    handle_galaxy_config_kwds(galaxy_config)

            if self.use_uwsgi:
                server_wrapper = launch_uwsgi(
                    galaxy_config,
                    tempdir=tempdir,
                    config_object=config_object,
                )
            else:
                # ---- Build Application --------------------------------------------------
                self.app = build_galaxy_app(galaxy_config)
                server_wrapper = launch_server(
                    self.app,
                    buildapp.app_factory,
                    galaxy_config,
                    config_object=config_object,
                )
                log.info("Functional tests will be run against external Galaxy server %s:%s" % (server_wrapper.host, server_wrapper.port))
            self.server_wrappers.append(server_wrapper)
        else:
            log.info("Functional tests will be run against test managed Galaxy server %s" % self.external_galaxy)
            # Ensure test file directory setup even though galaxy config isn't built.
            ensure_test_file_dir_set()

    def _ensure_config_object(self, config_object):
        if config_object is None:
            config_object = self
        return config_object

    def setup_shed_tools(self, testing_migrated_tools=False, testing_installed_tools=True):
        setup_shed_tools_for_test(
            self.app,
            self.galaxy_test_tmp_dir,
            testing_migrated_tools,
            testing_installed_tools
        )

    def build_tool_tests(self, testing_shed_tools=None, return_test_classes=False):
        if self.app is None:
            return

        if testing_shed_tools is None:
            testing_shed_tools = getattr(self, "testing_shed_tools", False)

        # We must make sure that functional.test_toolbox is always imported after
        # database_contexts.galaxy_content is set (which occurs in this method above).
        # If functional.test_toolbox is imported before database_contexts.galaxy_content
        # is set, sa_session will be None in all methods that use it.
        import functional.test_toolbox
        functional.test_toolbox.toolbox = self.app.toolbox
        # When testing data managers, do not test toolbox.
        test_classes = functional.test_toolbox.build_tests(
            app=self.app,
            testing_shed_tools=testing_shed_tools,
            master_api_key=get_master_api_key(),
            user_api_key=get_user_api_key(),
        )
        if return_test_classes:
            return test_classes
        return functional.test_toolbox

    def run_tool_test(self, tool_id, index=0, resource_parameters={}):
        host, port, url = target_url_parts()
        galaxy_interactor_kwds = {
            "galaxy_url": url,
            "master_api_key": get_master_api_key(),
            "api_key": get_user_api_key(),
            "keep_outputs_dir": None,
        }
        galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
        verify_tool(
            tool_id=tool_id,
            test_index=index,
            galaxy_interactor=galaxy_interactor,
            resource_parameters=resource_parameters
        )


def drive_test(test_driver_class):
    """Instantiate driver class, run, and exit appropriately."""
    test_driver = test_driver_class()
    sys.exit(test_driver.run())


def setup_keep_outdir():
    keep_outdir = os.environ.get('GALAXY_TEST_SAVE', '')
    if keep_outdir > '':
        try:
            os.makedirs(keep_outdir)
        except Exception:
            pass
    return keep_outdir


def target_url_parts():
    host = socket.gethostbyname(os.environ.get('GALAXY_TEST_HOST', DEFAULT_WEB_HOST))
    port = os.environ.get('GALAXY_TEST_PORT')
    default_url = "http://%s:%s" % (host, port)
    url = os.environ.get('GALAXY_TEST_EXTERNAL', default_url)
    return host, port, url


__all__ = (
    "copy_database_template",
    "build_logger",
    "drive_test",
    "FRAMEWORK_UPLOAD_TOOL_CONF",
    "FRAMEWORK_SAMPLE_TOOLS_CONF",
    "FRAMEWORK_DATATYPES_CONF",
    "database_conf",
    "get_webapp_global_conf",
    "nose_config_and_run",
    "setup_keep_outdir",
    "setup_galaxy_config",
    "target_url_parts",
    "TestDriver",
    "wait_for_http_server",
)
