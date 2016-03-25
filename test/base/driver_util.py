"""Scripts for drivers of Galaxy functional tests."""

import tempfile
import os
import logging


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


__all__ = [
    "configure_environment",
    "build_logger"
]
