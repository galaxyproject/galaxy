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
    Facade for common database schema migration operations on the gxy branch.
    When the gxy and tsi branches are persisted in the same database, some
    alembic commands will display output on the state on both branches (e.g.
    history, version, dbversion). The upgrade command is executed on both
    branches: gxy and tsi (the upgrade command ensures the branch has been
    initialized by stamping its version in the alembic_version table).
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.alembic_config = self._get_alembic_cfg()
        self._set_dburl(config_file)
        self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)

    def upgrade(self, args: argparse.Namespace) -> None:
        def upgrade_to_revision(rev):
            command.upgrade(self.alembic_config, rev, args.sql)

        if args.revision:
            revision = self._parse_revision(args.revision)
            upgrade_to_revision(revision)
        else:
            self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)
            upgrade_to_revision("gxy@head")
            try:
                self.alembic_config.set_main_option("sqlalchemy.url", self.tsi_url)
                upgrade_to_revision("tsi@head")
            finally:
                self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)

    def downgrade(self, args: argparse.Namespace) -> None:
        revision = self._parse_revision(args.revision)
        command.downgrade(self.alembic_config, revision, args.sql)

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
