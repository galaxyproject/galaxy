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
