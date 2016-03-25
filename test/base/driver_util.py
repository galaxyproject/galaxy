"""Scripts for drivers of Galaxy functional tests."""

import httplib
import logging
import os
import random
import shutil
import socket
import sys
import tempfile
import threading
import time

from six.moves.urllib.request import urlretrieve

import nose.config
import nose.core
import nose.loader
import nose.plugins.manager

from paste import httpserver

from .nose_util import run
from .instrument import StructuredTestDataPlugin

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))

DEFAULT_LOCALES = "en"


def setup_tool_shed_tmp_dir():
    tool_shed_test_tmp_dir = os.environ.get('TOOL_SHED_TEST_TMP_DIR', None)
    if tool_shed_test_tmp_dir is None:
        tool_shed_test_tmp_dir = tempfile.mkdtemp()
    # Here's the directory where everything happens.  Temporary directories are created within this directory to contain
    # the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
    # the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
    os.environ[ 'TOOL_SHED_TEST_TMP_DIR' ] = tool_shed_test_tmp_dir
    return tool_shed_test_tmp_dir


def configure_environment():
    """Hack up environment for test cases."""
    # no op remove if unused
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = DEFAULT_LOCALES


def build_logger():
    """Build a logger for test driver script."""
    return logging.getLogger("test_driver")


def nose_config_and_run( argv=None, env=None, ignore_files=[], plugins=None ):
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
    test_config.plugins.addPlugin( StructuredTestDataPlugin() )
    test_config.configure( argv )

    result = run( test_config )

    success = result.wasSuccessful()
    return success


def copy_database_template( source, db_path ):
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
        urlretrieve(source, db_path)
    else:
        raise Exception( "Failed to copy database template from source %s" % source )


def galaxy_database_conf(db_path):
    """Find (and populate if needed) Galaxy database connection."""
    database_auto_migrate = False
    if 'GALAXY_TEST_DBURI' in os.environ:
        database_connection = os.environ['GALAXY_TEST_DBURI']
    else:
        db_path = os.path.join(db_path, 'universe.sqlite')
        if 'GALAXY_TEST_DB_TEMPLATE' in os.environ:
            # Middle ground between recreating a completely new
            # database and pointing at existing database with
            # GALAXY_TEST_DBURI. The former requires a lot of setup
            # time, the latter results in test failures in certain
            # cases (namely tool shed tests expecting clean database).
            copy_database_template(os.environ['GALAXY_TEST_DB_TEMPLATE'], db_path)
            database_auto_migrate = True
        database_connection = 'sqlite:///%s' % db_path
    return database_connection, database_auto_migrate


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
        static_style_dir=os.path.join(static_dir, 'june_2007_style', 'blue'),
        static_robots_txt=os.path.join(static_dir, 'robots.txt'),
    )


def get_webapp_global_conf():
    """Get the global_conf dictionary sent to ``app_factory``."""
    # (was originally sent 'dict()') - nothing here for now except static settings
    global_conf = dict()
    global_conf.update( _get_static_settings() )
    return global_conf


def wait_for_http_server(host, port):
    """Wait for an HTTP server to boot up."""
    # Test if the server is up
    for i in range( 10 ):
        # directly test the app, not the proxy
        conn = httplib.HTTPConnection(host, port)
        conn.request( "GET", "/" )
        if conn.getresponse().status == 200:
            break
        time.sleep( 0.1 )
    else:
        template = "Test HTTP server on host %s and port %s did not return '200 OK' after 10 tries"
        message = template % (host, port)
        raise Exception(message)


def serve_webapp(webapp, port=None, host=None):
    """Serve the webapp on a recommend port or a free one.

    Return the port the webapp is running one.
    """
    server = None
    if port is not None:
        server = httpserver.serve( webapp, host=host, port=port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                port = str( random.randint( 8000, 10000 ) )
                server = httpserver.serve( webapp, host=host, port=port, start_loop=False )
                break
            except socket.error, e:
                if e[0] == 98:
                    continue
                raise
        else:
            raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % ( 8000, 1000 ) )

    t = threading.Thread( target=server.serve_forever )
    t.start()

    return server, port

__all__ = [
    "configure_environment",
    "copy_database_template",
    "build_logger",
    "galaxy_database_conf",
    "get_webapp_global_conf",
    "nose_config_and_run",
    "wait_for_http_server",
]
