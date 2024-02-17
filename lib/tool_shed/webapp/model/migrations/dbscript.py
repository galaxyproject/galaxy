import logging
import os
import sys
from argparse import Namespace
from typing import Optional

from galaxy.model.migrations.base import (
    BaseCommand,
    BaseDbScript,
    BaseParserBuilder,
)
from tool_shed.webapp.model.migrations import verify_database
from tool_shed.webapp.model.migrations.scripts import (
    get_dburl,
    get_dburl_from_file,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

CONFIG_FILE_ARG = "--toolshed-config"

# Update this dict with tags for each new release.
# Note: the key should NOT be a prefix of an existing revision hash in alembic/versions/.
# For example, if we have a hash 231xxxxxxxxx and use 231 as the key for release 23.1,
# then using 231 as a partial revision identifier like `sh manage_toolshed_db.sh upgrade 231`
# will map to release 23.1 instead of revision 231xxxxxxxxx.
REVISION_TAGS = {
    "release_23.1": "base",
    "23.1": "base",
}


class ParserBuilder(BaseParserBuilder):
    def _get_command_object(self):
        return Command()


class Command(BaseCommand):
    def init(self, args: Namespace) -> None:
        url = get_dburl(sys.argv, os.getcwd())
        verify_database(url)

    def _get_dbscript(self, config_file: str) -> BaseDbScript:
        return DbScript(config_file)


class DbScript(BaseDbScript):
    def _set_dburl(self, config_file: Optional[str] = None) -> None:
        self.url = get_dburl_from_file(os.getcwd(), config_file)
        self.alembic_config.set_main_option("sqlalchemy.url", self.url)

    def _upgrade_to_head(self, is_sql_mode: bool) -> None:
        self.alembic_config.set_main_option("sqlalchemy.url", self.url)
        self._upgrade_to_revision("head", is_sql_mode)

    def _revision_tags(self):
        return REVISION_TAGS
