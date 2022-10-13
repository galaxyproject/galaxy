import logging
import os
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import Optional

import alembic
from alembic import command
from alembic.config import Config

from galaxy.model.migrations import verify_databases_via_script
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

    def upgrade(self, args: Namespace) -> None:
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

    def downgrade(self, args: Namespace) -> None:
        revision = self._parse_revision(args.revision)
        command.downgrade(self.alembic_config, revision, args.sql)

    def revision(self, args: Namespace) -> None:
        """Create revision script for the gxy branch only."""
        command.revision(self.alembic_config, message=args.message, rev_id=args.rev_id, head="gxy@head")

    def version(self, args: Namespace) -> None:
        command.heads(self.alembic_config, verbose=args.verbose)

    def dbversion(self, args: Namespace) -> None:
        command.current(self.alembic_config, verbose=args.verbose)

    def history(self, args: Namespace) -> None:
        command.history(self.alembic_config, verbose=args.verbose, indicate_current=args.indicate_current)

    def show(self, args: Namespace) -> None:
        command.show(self.alembic_config, args.revision)

    def _get_alembic_cfg(self) -> Config:
        config_file = os.getenv("ALEMBIC_CONFIG")
        if not config_file:
            config_file = os.path.join(os.path.dirname(__file__), "alembic.ini")
            config_file = os.path.abspath(config_file)
        return Config(config_file)

    def _set_dburl(self, config_file: Optional[str] = None) -> None:
        gxy_config, tsi_config, _ = get_configuration_from_file(os.getcwd(), config_file)
        self.gxy_url = gxy_config.url
        self.tsi_url = tsi_config.url

    def _parse_revision(self, rev: str) -> str:
        # Relative revision identifier requires a branch label
        if rev.startswith("+") or rev.startswith("-"):
            return f"gxy@{rev}"
        # Check if it's a tag, leave unchanged if not
        rev = REVISION_TAGS.get(rev, rev)
        return rev


class ParserBuilder:
    """
    Assembler object that simplifies the construction of an argument parser for db/db_dev migration scripts.
    """

    def __init__(self, parser, subcommand_required=True):
        self.parser = parser
        self.subparsers = parser.add_subparsers(required=subcommand_required)
        self._init_arg_parsers()

    def add_upgrade_command(self):
        parser = self._add_parser(
            "upgrade",
            Command.upgrade,
            "Upgrade to a later version",
            parents=[self._sql_arg_parser],
        )
        parser.add_argument("revision", help="Revision identifier or release tag", nargs="?")

    def add_downgrade_command(self):
        parser = self._add_parser(
            "downgrade",
            Command.downgrade,
            "Revert to a previous version",
            parents=[self._sql_arg_parser],
        )
        parser.add_argument("revision", help="Revision identifier or release tag")

    def add_version_command(self):
        self._add_parser(
            "version",
            Command.version,
            "Show the head revision in the migrations script directory",
            aliases=["v"],
            parents=[self._verbose_arg_parser],
        )

    def add_dbversion_command(self):
        self._add_parser(
            "dbversion",
            Command.dbversion,
            "Show the current revision for Galaxy's database",
            aliases=["dv"],
            parents=[self._verbose_arg_parser],
        )

    def add_init_command(self):
        self._add_parser(
            "init",
            Command.init,
            "Initialize empty database(s)",
        )

    def add_revision_command(self):
        parser = self._add_parser("revision", help="Create a new revision file", func=Command.revision)
        parser.add_argument("-m", "--message", help="Message string to use with 'revision'", required=True)
        parser.add_argument(
            "--rev-id",
            help="Specify a revision id instead of generating one (This option is for testing purposes only)",
        )

    def add_history_command(self):
        parser = self._add_parser(
            "history",
            Command.history,
            "List revision scripts in chronological order",
            aliases=["h"],
            parents=[self._verbose_arg_parser],
        )
        parser.add_argument("-i", "--indicate-current", help="Indicate current revision", action="store_true")

    def add_show_command(self):
        parser = self._add_parser(
            "show",
            Command.show,
            "Show the revision(s) denoted by the given symbol",
            aliases=["s"],
        )
        parser.add_argument("revision", help="Revision identifier")

    def _init_arg_parsers(self):
        self._verbose_arg_parser = self._make_verbose_arg_parser()
        self._sql_arg_parser = self._make_sql_arg_parser()

    def _make_verbose_arg_parser(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument("-v", "--verbose", action="store_true", help="Display more detailed output")
        return parser

    def _make_sql_arg_parser(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            "--sql",
            action="store_true",
            help="Don't emit SQL to database - dump to standard output/file instead. See Alembic docs on offline mode.",
        )
        return parser

    def _add_parser(self, command, func, help, aliases=None, parents=None):
        aliases = aliases or []
        parents = parents or []
        parser = self.subparsers.add_parser(command, aliases=aliases, help=help, parents=parents)
        parser.set_defaults(func=func)
        return parser


class Command:
    """Execute commands."""

    @staticmethod
    def upgrade(args: Namespace) -> None:
        Command._exec_command("upgrade", args)

    @staticmethod
    def downgrade(args: Namespace) -> None:
        Command._exec_command("downgrade", args)

    @staticmethod
    def version(args: Namespace) -> None:
        Command._exec_command("version", args)

    @staticmethod
    def dbversion(args: Namespace) -> None:
        Command._exec_command("dbversion", args)

    @staticmethod
    def init(args: Namespace) -> None:
        gxy_config, tsi_config, is_auto_migrate = get_configuration(sys.argv, os.getcwd())
        verify_databases_via_script(gxy_config, tsi_config, is_auto_migrate)

    @staticmethod
    def revision(args: Namespace) -> None:
        Command._exec_command("revision", args)

    @staticmethod
    def history(args: Namespace) -> None:
        Command._exec_command("history", args)

    @staticmethod
    def show(args: Namespace) -> None:
        Command._exec_command("show", args)

    @staticmethod
    def _exec_command(command: str, args: Namespace) -> None:
        dbscript = DbScript(args.config)
        try:
            getattr(dbscript, command)(args)
        except alembic.util.exc.CommandError as e:
            if hasattr(args, "raiseerr") and args.raiseerr:
                raise
            else:
                log.error(e)
                print(f"FAILED: {str(e)}")
                sys.exit(1)
