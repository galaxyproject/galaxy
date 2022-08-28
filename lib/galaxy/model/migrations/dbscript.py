import argparse
import os
import sys
from typing import (
    List,
    Optional,
    Tuple,
)

import alembic.config
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from galaxy.model.database_utils import (
    database_exists,
    is_one_database,
)
from galaxy.model.migrations import (
    AlembicManager,
    DatabaseConfig,
    DatabaseStateCache,
    GXY,
    IncorrectVersionError,
    NoVersionTableError,
    SQLALCHEMYMIGRATE_LAST_VERSION_GXY,
    TSI,
)
from galaxy.util.properties import (
    find_config_file,
    get_data_dir,
    load_app_properties,
)

DEFAULT_CONFIG_NAMES = ["galaxy", "universe_wsgi"]
CONFIG_FILE_ARG = "--galaxy-config"
CONFIG_DIR_NAME = "config"
GXY_CONFIG_PREFIX = "GALAXY_CONFIG_"
TSI_CONFIG_PREFIX = "GALAXY_INSTALL_CONFIG_"


class DbScript:
    """
    Used to manage the gxy db.
    The upgrade command is called on both: gxy and tsi. Reason: if this is the first alembic command on this branch,
    the upgrade command will stamp the alembic_version table: we need that for both branches.
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.alembic_config = self._get_alembic_cfg()
        self._set_dburl(config_file)

    def upgrade(self, args: argparse.Namespace) -> None:
        revision = self._parse_revision(args.revision)
        command.upgrade(self.alembic_config, revision, args.sql)

    def downgrade(self, args: argparse.Namespace) -> None:
        command.downgrade(self.alembic_config, args.revision, args.sql)

    def revision(self, args: argparse.Namespace) -> None:
        """Create revision script for the gxy branch only."""
        command.revision(self.alembic_config, message=args.message, rev_id=args.rev_id, head="gxy@head")

    def version(self, args: argparse.Namespace) -> None:
        command.heads(self.alembic_config, verbose=args.verbose)

    def dbversion(self, args: argparse.Namespace) -> None:
        command.current(self.alembic_config, verbose=args.verbose)

    def history(self, args: argparse.Namespace) -> None:
        command.history(self.alembic_config, verbose=args.verbose, indicate_current=args.indicate_current)

    def show(self, args: argparse.Namespace) -> None:
        command.show(self.alembic_config, args.revision)

    def _get_alembic_cfg(self):
        config_file = os.getenv("ALEMBIC_CONFIG")
        if not config_file:
            config_file = os.path.join(os.path.dirname(__file__), "alembic.ini")
            config_file = os.path.abspath(config_file)
        return Config(config_file)

    def _set_dburl(self, config_file: Optional[str] = None) -> None:
        gxy_config, tsi_config = self._get_configuration(config_file)
        self.gxy_url = gxy_config.url
        self.tsi_url = tsi_config.url
        self._set_url(self.gxy_url)

    def _set_url(self, url: str) -> None:
        self.alembic_config.set_main_option("sqlalchemy.url", url)

    def _parse_revision(self, rev):
        # Relative revision identifier requires a branch label
        if rev.startswith("+") or rev.startswith("-"):
            return f"gxy@{rev}"
        return rev

    def _get_configuration(self, config_file: Optional[str] = None) -> Tuple[DatabaseConfig, DatabaseConfig]:
        """
        Return a 2-item-tuple with configuration values used for managing databases.
        """
        if config_file is None:
            cwd = os.getcwd()
            cwds = [cwd, os.path.join(cwd, CONFIG_DIR_NAME)]
            config_file = find_config_file(DEFAULT_CONFIG_NAMES, dirs=cwds)

        # load gxy properties and auto-migrate
        properties = load_app_properties(config_file=config_file, config_prefix=GXY_CONFIG_PREFIX)
        default_url = f"sqlite:///{os.path.join(get_data_dir(properties), 'universe.sqlite')}?isolation_level=IMMEDIATE"
        url = properties.get("database_connection", default_url)
        template = properties.get("database_template", None)
        encoding = properties.get("database_encoding", None)
        gxy_config = DatabaseConfig(url, template, encoding)

        # load tsi properties
        properties = load_app_properties(config_file=config_file, config_prefix=TSI_CONFIG_PREFIX)
        default_url = gxy_config.url
        url = properties.get("install_database_connection", default_url)
        template = properties.get("database_template", None)
        encoding = properties.get("database_encoding", None)
        tsi_config = DatabaseConfig(url, template, encoding)

        return (gxy_config, tsi_config)
