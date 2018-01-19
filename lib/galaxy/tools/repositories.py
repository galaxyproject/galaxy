"""Provides a subset of app for verifying tools."""
import os
import shutil
import tempfile
from contextlib import contextmanager

from galaxy.datatypes.registry import Registry
from galaxy.tools.data import ToolDataTableManager
from galaxy.util.bunch import Bunch
from galaxy.util.dbkeys import GenomeBuilds


class ValidationContext(object):
    """Minimal App object for tool validation."""

    def __init__(self, app_name,
                 security,
                 model,
                 tool_data_path,
                 shed_tool_data_path,
                 tool_data_tables=None,
                 registry=None,
                 hgweb_config_manager=None):
        self.name = app_name
        self.security = security
        self.model = model
        self.config = Bunch()
        self.config.tool_data_path = tool_data_path
        self.config.shed_tool_data_path = shed_tool_data_path
        _, self.config.tool_data_table_config = tempfile.mkstemp()
        _, self.config.shed_tool_data_table_config = tempfile.mkstemp()
        self.tool_data_tables = tool_data_tables
        self.datatypes_registry = registry or Registry()
        self.hgweb_config_manager = hgweb_config_manager
        _, self.config.len_file_path = tempfile.mkstemp()
        _, self.config.builds_file_path = tempfile.mkstemp()
        self.genome_builds = GenomeBuilds(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        cleanup_paths = {self.config.builds_file_path,
                         self.config.len_file_path,
                         self.config.tool_data_table_config,
                         self.config.shed_tool_data_table_config}
        for path in cleanup_paths:
            try:
                os.remove(path)
            except Exception:
                pass

    @staticmethod
    @contextmanager
    def from_app(app, work_dir=None):
        cleanup = False
        if not work_dir:
            work_dir = tempfile.mkdtemp()
            cleanup = True
        tool_data_tables = ToolDataTableManager(work_dir)
        with ValidationContext(app_name=app.name,
                               security=app.security,
                               model=app.model,
                               tool_data_path=work_dir,
                               shed_tool_data_path=work_dir,
                               tool_data_tables=tool_data_tables,
                               hgweb_config_manager=getattr(app, 'hgweb_config_manager', None)
                               ) as app:
            yield app
        if cleanup:
            shutil.rmtree(work_dir, ignore_errors=True)
