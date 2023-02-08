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

    def _upgrade_to_head(self, is_sql_mode: bool):
        self.alembic_config.set_main_option("sqlalchemy.url", self.url)
        self._upgrade_to_revision("head", is_sql_mode)
