"""Create a smaller version of app for verifying tools"""
import os
import shutil
import tempfile

from contextlib import contextmanager

from .bunch import Bunch
from galaxy.datatypes.registry import Registry
from galaxy.tools.data import ToolDataTableManager


class MiniApp(object):
    """Minimal App object for tool validation."""

    def __init__(self, app_name, security, tool_data_path, shed_tool_data_path, tool_data_tables=None, registry=None):
        self.name = app_name
        self.security = security
        self.config = Bunch()
        self.config.tool_data_path = tool_data_path
        self.config.shed_tool_data_path = shed_tool_data_path
        _, self.config.tool_data_table_config = tempfile.mkstemp()
        _, self.config.shed_tool_data_table_config = tempfile.mkstemp()
        self.tool_data_tables = tool_data_tables
        self.datatypes_registry=registry or Registry()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            os.remove(self.config.tool_data_table_config)
            if self.config.shed_tool_data_table_config != self.config.tool_data_table_config:
                os.remove(self.config.shed_tool_data_table_config)
        except Exception:
            pass

    @contextmanager
    @staticmethod
    def from_app(app, work_dir=None):
        cleanup = False
        if not work_dir:
            work_dir = tempfile.mkdtemp()
            cleanup = True
        tool_data_tables = ToolDataTableManager(work_dir)
        app_name = app.name
        yield MiniApp(app_name=app_name,
                       security=app.security,
                       tool_data_path=work_dir,
                       shed_tool_data_path=work_dir,
                       tool_data_tables=tool_data_tables)
        if cleanup:
            shutil.rmtree(work_dir, ignore_errors=True)