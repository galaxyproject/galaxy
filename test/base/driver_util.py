"""Scripts for drivers of Galaxy functional tests."""

import logging
import os
import sys
import tempfile

import nose.config
import nose.core
import nose.loader
import nose.plugins.manager

from .nose_util import run
from .instrument import StructuredTestDataPlugin


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


__all__ = [
    "configure_environment",
    "build_logger",
    "nose_config_and_run",
]
