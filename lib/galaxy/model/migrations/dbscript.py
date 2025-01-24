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

# Update this dict with tags for each new release.
# Note: the key should NOT be a prefix of an existing revision hash in alembic/versions_gxy/.
# For example, if we have a hash 231xxxxxxxxx and use 231 as the key for release 23.1,
# then using 231 as a partial revision identifier like `sh manage_db.sh upgrade 231`
# will map to release 23.1 instead of revision 231xxxxxxxxx.
REVISION_TAGS = {
    "release_22.01": "base",
    "22.01": "base",
    "release_22.05": "186d4835587b",
    "22.05": "186d4835587b",
    "release_23.0": "caa7742f7bca",
    "23.0": "caa7742f7bca",
    "release_23.1": "e93c5d0b47a9",
    "23.1": "e93c5d0b47a9",
    "release_23.2": "8a19186a6ee7",
    "23.2": "8a19186a6ee7",
    "release_24.0": "55f02fd8ab6c",
    "24.0": "55f02fd8ab6c",
    "release_24.1": "04288b6a5b25",
    "24.1": "04288b6a5b25",
    "release_24.2": "75348cfb3715",
    "24.2": "75348cfb3715",
}


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
        return REVISION_TAGS

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
