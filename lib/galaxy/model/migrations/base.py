"""
Shared code for galaxy and tool shed migrations.
"""

import abc
import logging
import os
import sys
import urllib.parse
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import (
    cast,
    Dict,
    Iterable,
    List,
    Optional,
    Union,
)

import alembic
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.script.base import Script
from sqlalchemy import (
    MetaData,
    Table,
    text,
)
from sqlalchemy.engine import (
    Connection,
    Engine,
)

ALEMBIC_TABLE = "alembic_version"
SQLALCHEMYMIGRATE_TABLE = "migrate_version"

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class BaseParserBuilder(abc.ABC):
    """
    Assembler object that simplifies the construction of an argument parser for database migration scripts.
    """

    @abc.abstractmethod
    def _get_command_object(self): ...

    def __init__(self, parser, subcommand_required=True):
        self._cmd = self._get_command_object()
        self.parser = parser
        self.subparsers = parser.add_subparsers(required=subcommand_required)
        self._init_arg_parsers()

    def add_upgrade_command(self, dev_options=False):
        parents = self._get_upgrade_downgrade_arg_parsers(dev_options)
        parser = self._add_parser(
            "upgrade",
            self._cmd.upgrade,
            "Upgrade to a later version",
            parents=parents,
        )
        parser.add_argument("revision", help="Revision identifier or release tag", nargs="?")

    def add_downgrade_command(self, dev_options=False):
        parents = self._get_upgrade_downgrade_arg_parsers(dev_options)
        parser = self._add_parser(
            "downgrade",
            self._cmd.downgrade,
            "Revert to a previous version",
            parents=parents,
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
        self._repair_arg_parser = self._make_repair_arg_parser()

    def _get_upgrade_downgrade_arg_parsers(self, dev_options):
        parsers = [self._sql_arg_parser]
        if dev_options:
            parsers.append(self._make_repair_arg_parser())
        return parsers

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

    def _make_repair_arg_parser(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            "--repair",
            action="store_true",
            help="""Skip revisions that conflict with the current state of the database (examples of
            conflict: creating an object that exists or dropping an object that does not exist).
            Note: implicitly created objects (such as those created by Alembic as part of ALTER
            statement workaround) that may have been left over will still raise an error. Such
            objects must be removed manually.
            """,
        )
        return parser

    def _add_parser(self, command, func, help, aliases=None, parents=None):
        aliases = aliases or []
        parents = parents or []
        parser = self.subparsers.add_parser(command, aliases=aliases, help=help, parents=parents)
        parser.set_defaults(func=func)
        return parser


class BaseDbScript(abc.ABC):
    """Facade for common database schema migration operations."""

    @abc.abstractmethod
    def _set_dburl(self, config_file: Optional[str] = None) -> None: ...

    @abc.abstractmethod
    def _upgrade_to_head(self, is_sql_mode: bool): ...

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.alembic_config = self._get_alembic_cfg()
        self._set_dburl(config_file)

    def revision(self, args: Namespace) -> None:
        head = self._add_branch_label("head")
        command.revision(self.alembic_config, message=args.message, rev_id=args.rev_id, head=head)

    def upgrade(self, args: Namespace) -> None:
        self._process_repair_arg(args)
        if args.revision:
            revision = self._parse_revision(args.revision)
            self._upgrade_to_revision(revision, args.sql)
        else:
            self._upgrade_to_head(args.sql)

    def downgrade(self, args: Namespace) -> None:
        self._process_repair_arg(args)
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

    def _process_repair_arg(self, args: Namespace) -> None:
        if "repair" in args and args.repair:
            self.alembic_config.set_main_option("repair", "1")


class BaseCommand(abc.ABC):
    @abc.abstractmethod
    def init(self, args: Namespace) -> None: ...

    @abc.abstractmethod
    def _get_dbscript(self, config_file: str) -> BaseDbScript: ...

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


class BaseAlembicManager(abc.ABC):
    """
    Alembic operations on one database.
    """

    @abc.abstractmethod
    def _get_alembic_root(self): ...

    @staticmethod
    def is_at_revision(engine: Engine, revision: Union[str, Iterable[str]]) -> bool:
        """
        True if revision is a subset of the set of version heads stored in the database.
        """
        revision = listify(revision)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            db_version_heads = context.get_current_heads()
            return set(revision) <= set(db_version_heads)

    def __init__(self, engine: Engine, config_dict: Optional[dict] = None) -> None:
        self.engine = engine
        self.alembic_cfg = self._load_config(config_dict)
        self.script_directory = ScriptDirectory.from_config(self.alembic_cfg)
        self._db_heads: Optional[Iterable[str]]
        self._reset_db_heads()

    @property
    def db_heads(self) -> Optional[Iterable]:
        if self._db_heads is None:  # Explicitly check for None: could be an empty tuple.
            with self.engine.connect() as conn:
                context: MigrationContext = MigrationContext.configure(conn)
                self._db_heads = context.get_current_heads()
            # We get a tuple as long as we use branches. Otherwise, we'd get a single value.
            # listify() is a safeguard in case we stop using branches.
            self._db_heads = listify(self._db_heads)
        return self._db_heads

    def stamp_revision(self, revision: Union[str, Iterable[str]]) -> None:
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, revision)  # type: ignore[arg-type]  # https://alembic.sqlalchemy.org/en/latest/api/commands.html#alembic.command.stamp.params.revision
        self._reset_db_heads()

    def _load_config(self, config_dict: Optional[dict]) -> Config:
        alembic_root = self._get_alembic_root()
        _alembic_file = os.path.join(alembic_root, "alembic.ini")
        config = Config(_alembic_file)
        url = get_url_string(self.engine)
        config.set_main_option("sqlalchemy.url", url)
        if config_dict:
            for key, value in config_dict.items():
                config.set_main_option(key, value)
        return config

    def _get_revision(self, revision_id: str) -> Optional[Script]:
        try:
            return self.script_directory.get_revision(revision_id)
        except alembic.util.exc.CommandError as e:
            log.error(f"Revision {revision_id} not found in the script directory")
            raise e

    def _reset_db_heads(self) -> None:
        self._db_heads = None


class DatabaseStateCache:
    """
    Snapshot of database state.
    """

    def __init__(self, engine: Engine) -> None:
        self._load_db(engine)

    @property
    def tables(self) -> Dict[str, Table]:
        return self.db_metadata.tables

    def is_database_empty(self) -> bool:
        return not bool(self.db_metadata.tables)

    def contains_only_kombu_tables(self) -> bool:
        return metadata_contains_only_kombu_tables(self.db_metadata)

    def has_alembic_version_table(self) -> bool:
        return ALEMBIC_TABLE in self.db_metadata.tables

    def has_sqlalchemymigrate_version_table(self) -> bool:
        return SQLALCHEMYMIGRATE_TABLE in self.db_metadata.tables

    def is_last_sqlalchemymigrate_version(self, last_version: int) -> bool:
        return self.sqlalchemymigrate_version == last_version

    def _load_db(self, engine: Engine) -> None:
        with engine.connect() as conn:
            self.db_metadata = self._load_db_metadata(conn)
            self.sqlalchemymigrate_version = self._load_sqlalchemymigrate_version(conn)

    def _load_db_metadata(self, conn: Connection) -> MetaData:
        metadata = MetaData()
        metadata.reflect(bind=conn)
        return metadata

    def _load_sqlalchemymigrate_version(self, conn: Connection) -> Optional[int]:
        if self.has_sqlalchemymigrate_version_table():
            sql = text(f"select version from {SQLALCHEMYMIGRATE_TABLE}")
            return conn.execute(sql).scalar()
        return None


def pop_arg_from_args(args: List[str], arg_name) -> Optional[str]:
    """
    Pop and return argument name and value from args if arg_name is in args.
    """
    if arg_name in args:
        pos = args.index(arg_name)
        args.pop(pos)  # pop argument name
        return args.pop(pos)  # pop and return argument value
    return None


def metadata_contains_only_kombu_tables(metadata: MetaData) -> bool:
    """
    Return True if metadata contains only kombu-related tables.
    (ref: https://github.com/galaxyproject/galaxy/issues/13689)
    """
    return all(table.startswith("kombu_") or table.startswith("sqlite_") for table in metadata.tables.keys())


def get_url_string(engine: Engine) -> str:
    db_url = engine.url.render_as_string(hide_password=False)
    return urllib.parse.unquote(db_url)


def load_metadata(metadata: MetaData, engine: Engine) -> None:
    with engine.begin() as conn:
        metadata.create_all(bind=conn)


def listify(data: Union[str, Iterable[str]]) -> Iterable[str]:
    if not isinstance(data, (list, tuple)):
        return [cast(str, data)]
    return data
