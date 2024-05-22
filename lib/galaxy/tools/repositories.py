"""Provides a subset of app for verifying tools."""

import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Optional

from galaxy.managers.dbkeys import GenomeBuilds
from galaxy.tools.data import ToolDataTableManager
from galaxy.util.bunch import Bunch


class ValidationContextConfig:
    tool_data_path: Optional[str]
    shed_tool_data_path: Optional[str]
    tool_data_table_config: str
    shed_tool_data_table_config: str
    interactivetools_enable: bool
    len_file_path: str
    builds_file_path: Optional[str]


class ValidationContext:
    """Minimal App object for tool validation."""

    is_webapp = True
    config: ValidationContextConfig

    def __init__(
        self,
        app_name: str,
        model,
        security,
        tool_data_path,
        shed_tool_data_path,
        tool_data_tables=None,
        registry=None,
        hgweb_config_manager=None,
        biotools_metadata_source=None,
    ):
        self.name = app_name
        self.model = model
        self.security = security
        self.config = ValidationContextConfig()
        self.config.tool_data_path = tool_data_path
        self.config.shed_tool_data_path = shed_tool_data_path
        self.temporary_path = tempfile.mkdtemp(prefix="tool_validation_")
        self.config.tool_data_table_config = os.path.join(self.temporary_path, "tool_data_table_conf.xml")
        self.config.shed_tool_data_table_config = os.path.join(self.temporary_path, "shed_tool_data_table_conf.xml")
        self.config.interactivetools_enable = True
        self.tool_data_tables = tool_data_tables
        self.tool_shed_registry = Bunch(tool_sheds={})
        self.datatypes_registry = registry
        self.hgweb_config_manager = hgweb_config_manager
        self.biotools_metadata_source = biotools_metadata_source
        self.config.len_file_path = os.path.join(self.temporary_path, "chromlen.txt")
        # If the builds file path is set to None, tools/__init__.py will load the default.
        # Otherwise it will attempt to load a nonexistent file and log an error. This does
        # not appear to be an issue with the len_file_path config option.
        self.config.builds_file_path = None
        self.genome_builds = GenomeBuilds(self)
        self.job_search = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.temporary_path)

    @staticmethod
    @contextmanager
    def from_app(app, work_dir=None):
        cleanup = False
        if not work_dir:
            work_dir = tempfile.mkdtemp()
            cleanup = True
        tool_data_tables = ToolDataTableManager(work_dir)
        try:
            with ValidationContext(
                app_name=app.name,
                security=app.security,
                model=getattr(app, "model", None),
                tool_data_path=work_dir,
                shed_tool_data_path=work_dir,
                tool_data_tables=tool_data_tables,
                registry=getattr(app, "datatypes_registry", None),
                hgweb_config_manager=getattr(app, "hgweb_config_manager", None),
                biotools_metadata_source=getattr(app, "biotools_metadata_source", None),
            ) as app:
                yield app
        finally:
            if cleanup:
                shutil.rmtree(work_dir, ignore_errors=True)
