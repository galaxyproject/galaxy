import logging
import os
import sys
from argparse import Namespace
from typing import Optional

from galaxy.model.migrations import verify_databases_via_script
from galaxy.model.migrations.base import (
    BaseCommand,
    BaseDbScript,
    BaseParserBuilder,
)
from galaxy.model.migrations.dbrevisions import REVISION_TAGS
from galaxy.model.migrations.scripts import (
    get_configuration,
    get_configuration_from_file,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

DEFAULT_CONFIG_NAMES = ["galaxy", "universe_wsgi"]
CONFIG_FILE_ARG = "--galaxy-config"
CONFIG_DIR_NAME = "config"
GXY_CONFIG_PREFIX = "GALAXY_CONFIG_"
TSI_CONFIG_PREFIX = "GALAXY_INSTALL_CONFIG_"


class ParserBuilder(BaseParserBuilder):
    def _get_command_object(self):
        return Command()


class Command(BaseCommand):
    def init(self, args: Namespace) -> None:
        gxy_config, tsi_config, is_auto_migrate = get_configuration(sys.argv, os.getcwd())
        verify_databases_via_script(gxy_config, tsi_config, is_auto_migrate)

    def _get_dbscript(self, config_file: str) -> BaseDbScript:
        return DbScript(config_file)


class DbScript(BaseDbScript):
    """
    Facade for common database schema migration operations on the gxy branch.
    When the gxy and tsi branches are persisted in the same database, some
    alembic commands will display output on the state on both branches (e.g.
    history, version, dbversion). The upgrade command is executed on both
    branches: gxy and tsi (the upgrade command ensures the branch has been
    initialized by stamping its version in the alembic_version table).
    """

    def _add_branch_label(self, revision_id: str) -> str:
        return f"gxy@{revision_id}"

    def _revision_tags(self):
        return {f"release_{k}": v for k, v in REVISION_TAGS.items()} | REVISION_TAGS

    def _set_dburl(self, config_file: Optional[str] = None) -> None:
        gxy_config, tsi_config, _ = get_configuration_from_file(os.getcwd(), config_file)
        self.gxy_url = gxy_config.url
        self.tsi_url = tsi_config.url
        self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)

    def _upgrade_to_head(self, is_sql_mode: bool):
        self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)
        self._upgrade_to_revision("gxy@head", is_sql_mode)
        try:
            self.alembic_config.set_main_option("sqlalchemy.url", self.tsi_url)
            self._upgrade_to_revision("tsi@head", is_sql_mode)
        finally:
            self.alembic_config.set_main_option("sqlalchemy.url", self.gxy_url)
