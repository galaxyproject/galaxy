import abc
import logging
import os
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    List,
    Optional,
)

import alembic
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class BaseParserBuilder(abc.ABC):
    """
    Assembler object that simplifies the construction of an argument parser for database migration scripts.
    """

    @abc.abstractmethod
    def _get_command_object(self):
        ...

    def __init__(self, parser, subcommand_required=True):
        self._cmd = self._get_command_object()
        self.parser = parser
        self.subparsers = parser.add_subparsers(required=subcommand_required)
        self._init_arg_parsers()

    def add_upgrade_command(self):
        parser = self._add_parser(
            "upgrade",
            self._cmd.upgrade,
            "Upgrade to a later version",
            parents=[self._sql_arg_parser],
        )
        parser.add_argument("revision", help="Revision identifier or release tag", nargs="?")

    def add_downgrade_command(self):
        parser = self._add_parser(
            "downgrade",
            self._cmd.downgrade,
            "Revert to a previous version",
            parents=[self._sql_arg_parser],
        )
        parser.add_argument("revision", help="Revision identifier or release tag")

    def add_version_command(self):
        self._add_parser(
            "version",
            self._cmd.version,
            "Show the head revision in the migrations script directory",
            aliases=["v"],
            parents=[self._verbose_arg_parser],
        )

    def add_dbversion_command(self):
        self._add_parser(
            "dbversion",
            self._cmd.dbversion,
            "Show the current revision for the database",
            aliases=["dv"],
            parents=[self._verbose_arg_parser],
        )

    def add_init_command(self):
        self._add_parser(
            "init",
            self._cmd.init,
            "Initialize empty database(s)",
        )

    def add_revision_command(self):
        parser = self._add_parser("revision", help="Create a new revision file", func=self._cmd.revision)
        parser.add_argument("-m", "--message", help="Message string to use with 'revision'", required=True)
        parser.add_argument(
            "--rev-id",
            help="Specify a revision id instead of generating one (This option is for testing purposes only)",
        )

    def add_history_command(self):
        parser = self._add_parser(
            "history",
            self._cmd.history,
            "List revision scripts in chronological order",
            aliases=["h"],
            parents=[self._verbose_arg_parser],
        )
        parser.add_argument("-i", "--indicate-current", help="Indicate current revision", action="store_true")

    def add_show_command(self):
        parser = self._add_parser(
            "show",
            self._cmd.show,
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


class BaseDbScript(abc.ABC):
    """
    Facade for common database schema migration operations on the gxy branch.
    When the gxy and tsi branches are persisted in the same database, some
    alembic commands will display output on the state on both branches (e.g.
    history, version, dbversion). The upgrade command is executed on both
    branches: gxy and tsi (the upgrade command ensures the branch has been
    initialized by stamping its version in the alembic_version table).
    """

    @abc.abstractmethod
    def _set_dburl(self, config_file: Optional[str] = None) -> None:
        ...

    @abc.abstractmethod
    def _upgrade_to_head(self, is_sql_mode: bool):
        ...

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.alembic_config = self._get_alembic_cfg()
        self._set_dburl(config_file)

    def revision(self, args: Namespace) -> None:
        head = self._add_branch_label("head")
        command.revision(self.alembic_config, message=args.message, rev_id=args.rev_id, head=head)

    def upgrade(self, args: Namespace) -> None:
        if args.revision:
            revision = self._parse_revision(args.revision)
            self._upgrade_to_revision(revision, args.sql)
        else:
            self._upgrade_to_head(args.sql)

    def downgrade(self, args: Namespace) -> None:
        revision = self._parse_revision(args.revision)
        command.downgrade(self.alembic_config, revision, args.sql)

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
            # We need to reference the runtime module because this is an abstract class,
            # so the path will be different for different concrete classes.
            module_file = sys.modules[self.__module__].__file__
            assert module_file
            config_file = os.path.join(os.path.dirname(module_file), "alembic.ini")
            # config_file = os.path.join(os.path.dirname(module.__file__), "alembic.ini")
            config_file = os.path.abspath(config_file)
        return Config(config_file)

    def _upgrade_to_revision(self, rev, is_sql_mode: bool):
        command.upgrade(self.alembic_config, rev, is_sql_mode)

    def _parse_revision(self, revision_id: str) -> str:
        # If branches are used, relative revision identifier requires a branch label.
        if revision_id.startswith("+") or revision_id.startswith("-"):
            return self._add_branch_label(revision_id)
        # Check if it's a tag, leave unchanged if not
        revision_id = self._revision_tags().get(revision_id, revision_id)
        return revision_id

    def _add_branch_label(self, revision_id: str) -> str:
        # Subclasses that need to add a branch label should overwrite this method.
        return revision_id

    def _revision_tags(self):
        # Subclasses that have revision tags should overwrite this method.
        return {}


class BaseCommand(abc.ABC):
    @abc.abstractmethod
    def init(self, args: Namespace) -> None:
        ...

    @abc.abstractmethod
    def _get_dbscript(self, config_file: str) -> BaseDbScript:
        ...

    def upgrade(self, args: Namespace) -> None:
        self._exec_command("upgrade", args)

    def downgrade(self, args: Namespace) -> None:
        self._exec_command("downgrade", args)

    def version(self, args: Namespace) -> None:
        self._exec_command("version", args)

    def dbversion(self, args: Namespace) -> None:
        self._exec_command("dbversion", args)

    def revision(self, args: Namespace) -> None:
        self._exec_command("revision", args)

    def history(self, args: Namespace) -> None:
        self._exec_command("history", args)

    def show(self, args: Namespace) -> None:
        self._exec_command("show", args)

    def _exec_command(self, command: str, args: Namespace) -> None:
        dbscript = self._get_dbscript(args.config)

        try:
            getattr(dbscript, command)(args)
        except alembic.util.exc.CommandError as e:
            if hasattr(args, "raiseerr") and args.raiseerr:
                raise
            else:
                log.error(e)
                print(f"FAILED: {str(e)}")
                sys.exit(1)


def pop_arg_from_args(args: List[str], arg_name) -> Optional[str]:
    """
    Pop and return argument name and value from args if arg_name is in args.
    """
    if arg_name in args:
        pos = args.index(arg_name)
        args.pop(pos)  # pop argument name
        return args.pop(pos)  # pop and return argument value
    return None
